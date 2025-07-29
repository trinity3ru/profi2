"""
Вспомогательные функции для парсера Profi.ru
"""
import logging
from typing import Optional, Dict, Any
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('parser.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def setup_logger(name: str) -> logging.Logger:
    """
    Создает и настраивает логгер для указанного модуля
    
    Args:
        name: Имя модуля для логгера
        
    Returns:
        logging.Logger: Настроенный логгер
    """
    return logging.getLogger(name)

def parse_price(price_str: str) -> Optional[int]:
    """
    Извлекает числовое значение цены из строки
    
    Args:
        price_str: Строка с ценой (например, "от 1000 ₽")
        
    Returns:
        Optional[int]: Числовое значение цены или None если не удалось распарсить
    """
    try:
        # Удаляем все нечисловые символы и конвертируем в int
        price = int(''.join(filter(str.isdigit, price_str)))
        return price
    except (ValueError, TypeError):
        logger.warning(f"Не удалось распарсить цену: {price_str}")
        return None

def format_order_message(order: Dict[str, Any]) -> str:
    """
    Форматирует данные заказа для отправки в Telegram
    
    Args:
        order: Словарь с данными заказа
        
    Returns:
        str: Отформатированное сообщение
    """
    message = (
        f"🔔 Новый заказ!\n\n"
        f"📝 Описание: {order.get('description', 'Нет описания')}\n"
        f"💰 Бюджет: {order.get('budget', 'Не указан')}\n"
        f"📍 Локация: {order.get('location', 'Не указана')}\n"
        f"🕒 Добавлено: {order.get('created_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}\n"
        f"🔗 Ссылка: {order.get('url', '#')}"
    )
    return message

def retry_on_exception(func):
    """
    Декоратор для повторных попыток выполнения функции при возникновении ошибок
    
    Args:
        func: Декорируемая функция
        
    Returns:
        wrapper: Обернутая функция с механизмом повторных попыток
    """
    from functools import wraps
    from time import sleep
    from config import MAX_RETRIES
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        retries = 0
        while retries < MAX_RETRIES:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                retries += 1
                if retries == MAX_RETRIES:
                    logger.error(f"Превышено максимальное количество попыток. Последняя ошибка: {str(e)}")
                    raise
                logger.warning(f"Попытка {retries}/{MAX_RETRIES} не удалась. Ошибка: {str(e)}")
                sleep(2 ** retries)  # Экспоненциальная задержка
    return wrapper 