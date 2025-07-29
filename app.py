from selenium import webdriver
from orders import get_orders
from telegram_bot import ProfiBot
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, reload_config, PROFI_LOGIN, PROFI_PASSWORD, PARSE_INTERVAL
import asyncio
import shutil
import logging
from datetime import datetime, time as dt_time
from auth.auth_service import AuthService
import time
from selenium.webdriver.support.ui import WebDriverWait

from orders import filter_orders
from config import ORDERS_URL

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ProfiApp:
    def __init__(self):
        """Инициализация приложения"""
        # Перезагружаем конфигурацию при старте
        reload_config()
        
        try:
            self.auth_service = AuthService()
            self.bot = ProfiBot()
            self.driver = None
            self.processed_orders = set()  # Множество для хранения уникальных идентификаторов заказов (ID + дата)
            self.work_start = dt_time(6, 0)  # 6:00
            self.work_end = dt_time(22, 0)   # 22:00
            self.update_interval = PARSE_INTERVAL  # Интервал обновления из конфига
            self.min_interval = 60  # Минимальный интервал (1 минута)
            self.max_interval = 3600  # Максимальный интервал (1 час)
            self.is_running = False
            self.max_memory_orders = 100  # Максимальное количество заказов в памяти
            logger.info("Приложение инициализировано")
        except Exception as e:
            logger.error(f"Ошибка при инициализации приложения: {str(e)}")
            raise
    
    def set_interval(self, seconds: int) -> bool:
        """
        Установка интервала обновления
        Args:
            seconds: Интервал в секундах
        Returns:
            bool: True если интервал установлен успешно
        """
        if self.min_interval <= seconds <= self.max_interval:
            self.update_interval = seconds
            logger.info(f"Установлен новый интервал обновления: {seconds} сек")
            return True
        return False
    
    def get_interval(self) -> int:
        """Получение текущего интервала обновления"""
        return self.update_interval

    def is_work_time(self) -> bool:
        """Проверка, находимся ли мы в рабочее время"""
        current_time = datetime.now().time()
        return self.work_start <= current_time <= self.work_end
    
    def get_order_unique_id(self, order: dict) -> str:
        """
        Создает уникальный идентификатор заказа на основе ID и даты публикации
        Args:
            order: Словарь с данными заказа
        Returns:
            str: Уникальный идентификатор заказа
        """
        order_id = order.get('id', '')
        date_posted = order.get('date_posted', '')
        title = order.get('title', '')[:50]  # Добавляем часть заголовка для уникальности
        unique_id = f"{order_id}_{date_posted}_{title}"
        logger.debug(f"Создан уникальный ID заказа: {unique_id}")
        return unique_id
    
    def cleanup_memory(self):
        """Очистка памяти от старых заказов"""
        if len(self.processed_orders) > self.max_memory_orders:
            # Оставляем только последние 50 заказов
            orders_list = list(self.processed_orders)
            self.processed_orders = set(orders_list[-50:])
            logger.info(f"Очищена память. Осталось {len(self.processed_orders)} заказов в памяти")
    
    async def process_orders(self):
        """Обработка заказов"""
        try:
            # Если драйвер не инициализирован, выполняем первичную авторизацию
            if not self.driver:
                logger.info("Выполняем первичную авторизацию")
                self.driver = self.auth_service.login()
                if not self.driver:
                    logger.error("Не удалось выполнить авторизацию")
                    return
            else:
                # Проверяем состояние драйвера
                if not self.is_driver_valid():
                    logger.error("Драйвер в недопустимом состоянии")
                    return
                
            # Переходим на страницу заказов
            try:
                self.driver.get(ORDERS_URL)
                # Ждем загрузки страницы
                WebDriverWait(self.driver, 10).until(
                    lambda d: 'Заказы' in d.title and d.execute_script('return document.readyState') == 'complete'
                )
            except Exception as e:
                logger.error(f"Ошибка при переходе на страницу заказов: {str(e)}")
                self.driver.save_screenshot('orders_page_error.png')
                return
                
            # Получаем только новые заказы
            new_orders = await get_orders(self.driver)
            if not new_orders:
                logger.info("Новых заказов не найдено")
                return
                
            logger.info(f"Найдено {len(new_orders)} новых заказов")
            
            # Фильтруем новые заказы
            filtered_orders = await filter_orders(new_orders)
            logger.info(f"После фильтрации осталось {len(filtered_orders)} новых заказов")
            
            # Отправляем отфильтрованные новые заказы
            sent_count = 0
            for order in filtered_orders:
                try:
                    logger.info(f"Отправляем новый заказ: {order.get('id', 'без ID')} - {order.get('title', 'Без названия')[:50]}")
                    await self.bot.send_order(order)
                    sent_count += 1
                except Exception as e:
                    logger.error(f"Ошибка при отправке заказа {order.get('id', 'без ID')}: {str(e)}")
            
            logger.info(f"Отправлено {sent_count} новых заказов из {len(filtered_orders)}")
            
        except Exception as e:
            logger.error(f"Ошибка при обработке заказов: {str(e)}")
            # При критической ошибке закрываем драйвер
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
                self.driver = None
    
    def is_driver_valid(self):
        """Проверка валидности драйвера"""
        try:
            # Пробуем получить текущий URL
            self.driver.current_url
            return True
        except:
            return False
    
    async def run(self):
        """Запуск приложения"""
        logger.info("Запуск приложения")
        self.is_running = True
        
        try:
            # Запускаем бота
            await self.bot.start()
            
            # Основной цикл работы
            while self.is_running:
                try:
                    await self.process_orders()
                    # Ждем указанный интервал без polling
                    await asyncio.sleep(self.update_interval)
                except Exception as e:
                    logger.error(f"Ошибка в цикле обработки: {str(e)}")
                    await asyncio.sleep(60)  # Ждем минуту перед следующей попыткой
                    
        except KeyboardInterrupt:
            logger.info("Получен сигнал завершения работы")
        except Exception as e:
            logger.error(f"Критическая ошибка: {str(e)}")
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Корректное завершение работы"""
        self.is_running = False
        if self.driver:
            self.driver.quit()
            logger.info("Драйвер закрыт")
        await self.bot.stop()
        logger.info("Приложение остановлено")

if __name__ == "__main__":
    app = ProfiApp()
    asyncio.run(app.run()) 