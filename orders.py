from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import logging
import asyncio
from datetime import datetime, timedelta
from config import ORDERS_URL, SELENIUM_IMPLICIT_WAIT
import re
import json
from pathlib import Path

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,  # Изменяем на DEBUG для подробного логирования
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def async_sleep(min_seconds=0.5, max_seconds=1):
    """Асинхронная задержка для имитации человеческого поведения"""
    await asyncio.sleep(min_seconds)

async def get_additional_info(driver, order_link):
    """
    Получение дополнительной информации о заказе со страницы заказа
    Args:
        driver: Selenium WebDriver
        order_link: Ссылка на заказ
    Returns:
        dict: Словарь с дополнительной информацией
    """
    try:
        # Сохраняем текущий URL
        current_url = driver.current_url
        
        # Переходим на страницу заказа
        driver.get(order_link)
        await async_sleep(1)  # Небольшая задержка для загрузки страницы
        
        # Ищем контейнер с дополнительной информацией
        additional_info = ''
        try:
            info_container = driver.find_element(By.CSS_SELECTOR, '[class*="order-card-additional-info__container"]')
            # Получаем текст из всех параграфов внутри контейнера
            paragraphs = info_container.find_elements(By.TAG_NAME, 'p')
            additional_info = ' '.join([p.text for p in paragraphs if p.text.strip()])
            logger.info(f"Получена дополнительная информация о заказе")
        except Exception as e:
            logger.warning(f"Не удалось найти дополнительную информацию: {str(e)}")
        
        # Возвращаемся на предыдущую страницу
        driver.get(current_url)
        await async_sleep(0.5)
        
        return {'additional_info': additional_info}
        
    except Exception as e:
        logger.error(f"Ошибка при получении дополнительной информации: {str(e)}")
        return {'additional_info': ''}

def extract_order_id_from_attributes(element_attributes, element_text, links_data):
    """
    Извлекает ID заказа из предварительно полученных атрибутов и данных
    Args:
        element_attributes: dict с атрибутами элемента
        element_text: str текст элемента
        links_data: list с данными ссылок
    Returns:
        str: ID заказа или None
    """
    try:
        logger.debug(f"Начинаем извлечение ID заказа из атрибутов")
        logger.debug(f"Атрибуты: {element_attributes}")
        logger.debug(f"Количество ссылок: {len(links_data)}")
        
        # Способ 1: Из data-testid атрибута (основной способ)
        test_id = element_attributes.get('data-testid')
        if test_id:
            logger.debug(f"Найден data-testid: {test_id}")
            # Ищем паттерн ID в data-testid (например: "80340822_order-snippet")
            id_match = re.search(r'(\d+)_order-snippet', test_id)
            if id_match:
                order_id = id_match.group(1)
                logger.debug(f"Извлечен ID из data-testid: {order_id}")
                return order_id
            
            # Альтернативный паттерн для data-testid
            id_match = re.search(r'(\d+)', test_id)
            if id_match:
                order_id = id_match.group(1)
                logger.debug(f"Извлечен ID из data-testid (альтернативный): {order_id}")
                return order_id
        
        # Способ 2: Из data-order-id атрибута
        order_id = element_attributes.get('data-order-id')
        if order_id:
            logger.debug(f"Найден data-order-id: {order_id}")
            return order_id
        
        # Способ 3: Из ссылок
        for i, link_data in enumerate(links_data):
            href = link_data.get('href')
            data_testid = link_data.get('data-testid')
            
            logger.debug(f"Обрабатываем ссылку {i+1}: href={href}, data-testid={data_testid}")
            
            if href:
                logger.debug(f"Найдена ссылка: {href}")
                # Извлекаем ID из URL
                id_match = re.search(r'/order/(\d+)', href)
                if id_match:
                    order_id = id_match.group(1)
                    logger.debug(f"Извлечен ID из ссылки: {order_id}")
                    return order_id
                
                # Альтернативный паттерн для URL
                id_match = re.search(r'o=(\d+)', href)
                if id_match:
                    order_id = id_match.group(1)
                    logger.debug(f"Извлечен ID из параметра o: {order_id}")
                    return order_id
            
            if data_testid:
                logger.debug(f"Найден data-testid в ссылке: {data_testid}")
                id_match = re.search(r'(\d+)_order-snippet', data_testid)
                if id_match:
                    order_id = id_match.group(1)
                    logger.debug(f"Извлечен ID из data-testid ссылки: {order_id}")
                    return order_id
        
        # Способ 4: Из data-id атрибута
        data_id = element_attributes.get('data-id')
        if data_id:
            logger.debug(f"Найден data-id: {data_id}")
            id_match = re.search(r'(\d+)', data_id)
            if id_match:
                order_id = id_match.group(1)
                logger.debug(f"Извлечен ID из data-id: {order_id}")
                return order_id
        
        # Способ 5: Из id атрибута
        element_id = element_attributes.get('id')
        if element_id:
            logger.debug(f"Найден id элемента: {element_id}")
            id_match = re.search(r'(\d+)', element_id)
            if id_match:
                order_id = id_match.group(1)
                logger.debug(f"Извлечен ID из id элемента: {order_id}")
                return order_id
        
        # Способ 6: Из текста элемента (ищем номер заказа)
        if element_text:
            logger.debug(f"Текст элемента: {element_text[:200]}...")  # Логируем первые 200 символов
            
            # Ищем паттерны номера заказа
            patterns = [
                r'№\s*(\d+)',  # № 123456
                r'Заказ\s*№?\s*(\d+)',  # Заказ № 123456
                r'ID:\s*(\d+)',  # ID: 123456
                r'Номер:\s*(\d+)',  # Номер: 123456
                r'\b(\d{6,})\b',  # Любое число из 6+ цифр
            ]
            
            for pattern in patterns:
                id_match = re.search(pattern, element_text, re.IGNORECASE)
                if id_match:
                    order_id = id_match.group(1)
                    logger.debug(f"Извлечен ID из текста по паттерну '{pattern}': {order_id}")
                    return order_id
        
        # Способ 7: Из onclick атрибута
        onclick = element_attributes.get('onclick')
        if onclick:
            logger.debug(f"Найден onclick: {onclick}")
            id_match = re.search(r'(\d+)', onclick)
            if id_match:
                order_id = id_match.group(1)
                logger.debug(f"Извлечен ID из onclick: {order_id}")
                return order_id
        
        logger.warning(f"Не удалось извлечь ID заказа из атрибутов")
        return None
            
    except Exception as e:
        logger.error(f"Ошибка при извлечении ID заказа из атрибутов: {str(e)}")
        return None

async def get_orders(driver):
    """Асинхронное получение заказов"""
    try:
        logger.info("Начинаем получение заказов")
        
        # Переходим на страницу заказов
        driver.get(ORDERS_URL)
        await async_sleep(2)  # Увеличиваем время ожидания загрузки страницы
        
        # Проверяем, что мы на правильной странице и она загрузилась
        try:
            WebDriverWait(driver, 10).until(
                lambda d: 'Заказы' in d.title and d.execute_script('return document.readyState') == 'complete'
            )
        except Exception as e:
            logger.error(f"Страница заказов не загрузилась: {str(e)}")
            driver.save_screenshot('orders_page_load_error.png')
            return []
            
        # Сохраняем HTML для отладки
        with open('orders_page.html', 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        
        # Пробуем разные селекторы для контейнера заказов
        container_selectors = [
            'div#BOARD_GRID_CONTAINER_ID',  # Основной селектор
            'div[class*="OrderSnippetStyles__CardContainer"]',  # Альтернативный селектор без динамического ID
            'div[data-testid="ORDER_SNIPPET"]'  # Селектор по data-testid
        ]
        
        orders_container = None
        for selector in container_selectors:
            try:
                orders_container = WebDriverWait(driver, SELENIUM_IMPLICIT_WAIT).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                if orders_container:
                    logger.info(f"Найден контейнер заказов по селектору: {selector}")
                    break
            except Exception as e:
                logger.debug(f"Селектор {selector} не найден: {str(e)}")
                continue
        
        if not orders_container:
            logger.error("Контейнер заказов не найден")
            return []
        
        # Получаем все заказы с повторными попытками при stale element
        order_selectors = [
            'div[class*="OrderSnippetStyles__CardContainer"]',  # Без динамического ID
            'div[data-testid="ORDER_SNIPPET"]',
            'div[class*="OrderSnippetContainerStyles__Container"]'  # Без динамического ID
        ]
        
        max_retries = 3
        retry_count = 0
        order_elements = []
        
        while retry_count < max_retries:
            try:
                for selector in order_selectors:
                    elements = WebDriverWait(driver, SELENIUM_IMPLICIT_WAIT).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
                    )
                    if elements:
                        order_elements = elements
                        logger.info(f"Найдены элементы заказов по селектору: {selector}")
                        break
                if order_elements:
                    break
            except Exception as e:
                retry_count += 1
                logger.warning(f"Попытка {retry_count} получения заказов не удалась: {str(e)}")
                if retry_count < max_retries:
                    await async_sleep(1)  # Ждем перед следующей попыткой
                    driver.refresh()  # Обновляем страницу
                    await async_sleep(1)  # Ждем загрузки
                else:
                    logger.error("Не удалось получить заказы после всех попыток")
                    return []
        
        logger.info(f"Найдено {len(order_elements)} заказов")
        
        # Ограничиваем количество заказов до 10 для ускорения
        max_orders = 10
        if len(order_elements) > max_orders:
            order_elements = order_elements[:max_orders]
            logger.info(f"Ограничиваем обработку до {max_orders} заказов")
        
        orders = []
        
        # Получаем все данные элементов сразу, чтобы избежать stale element reference
        logger.info("Получаем все данные элементов заказов...")
        
        # Фильтруем элементы - обрабатываем только те, которые содержат настоящие заказы
        valid_order_elements = []
        
        for i, element in enumerate(order_elements):
            try:
                # Проверяем, содержит ли элемент заголовок заказа
                has_title = False
                has_date = False
                
                try:
                    # Ищем заголовок по точному паттерну класса
                    title_element = element.find_element(By.CSS_SELECTOR, 'h3[class*="SubjectAndPriceStyles__SubjectsText"]')
                    has_title = True
                    logger.debug(f"Элемент {i+1}: Найден заголовок заказа")
                except:
                    logger.debug(f"Элемент {i+1}: Заголовок заказа не найден")
                
                try:
                    # Ищем дату по точному паттерну класса
                    date_element = element.find_element(By.CSS_SELECTOR, '[class*="Date__DateText"]')
                    has_date = True
                    logger.debug(f"Элемент {i+1}: Найдена дата заказа")
                except:
                    logger.debug(f"Элемент {i+1}: Дата заказа не найдена")
                
                # Добавляем элемент только если он содержит и заголовок, и дату
                if has_title and has_date:
                    valid_order_elements.append(element)
                    logger.info(f"Элемент {i+1}: Добавлен как валидный заказ")
                else:
                    logger.warning(f"Элемент {i+1}: Пропущен (не является заказом)")
                    
            except Exception as e:
                logger.error(f"Ошибка при проверке элемента {i+1}: {str(e)}")
                continue
        
        logger.info(f"Найдено {len(valid_order_elements)} валидных заказов из {len(order_elements)} элементов")
        
        # Ограничиваем количество обрабатываемых заказов
        max_orders = 10
        if len(valid_order_elements) > max_orders:
            valid_order_elements = valid_order_elements[:max_orders]
            logger.info(f"Ограничиваем обработку до {max_orders} заказов")
        
        new_orders = []
        processed_count = 0
        
        for i, element in enumerate(valid_order_elements):
            try:
                logger.info(f"Обрабатываем заказ {i+1}/{len(valid_order_elements)}")
                
                # Получаем все атрибуты и данные элемента сразу
                try:
                    # Получаем все атрибуты элемента
                    element_attributes = {}
                    try:
                        element_attributes['data-testid'] = element.get_attribute('data-testid')
                        element_attributes['data-order-id'] = element.get_attribute('data-order-id')
                        element_attributes['data-id'] = element.get_attribute('data-id')
                        element_attributes['id'] = element.get_attribute('id')
                        element_attributes['onclick'] = element.get_attribute('onclick')
                        
                        # Логируем найденные атрибуты для отладки
                        logger.debug(f"Заказ {i+1}: Атрибуты - data-testid: {element_attributes['data-testid']}, data-order-id: {element_attributes['data-order-id']}")
                        
                    except Exception as e:
                        logger.debug(f"Ошибка при получении атрибутов элемента {i+1}: {str(e)}")
                    
                    # Получаем текст элемента
                    try:
                        element_text = element.text
                        logger.debug(f"Заказ {i+1}: Текст элемента (первые 100 символов): {element_text[:100]}...")
                    except Exception as e:
                        logger.debug(f"Ошибка при получении текста элемента {i+1}: {str(e)}")
                        element_text = ""
                    
                    # Получаем ссылки
                    try:
                        # Ищем ссылки по частичному совпадению класса и атрибута
                        link_elements = element.find_elements(By.CSS_SELECTOR, 'a[data-testid*="_order-snippet"], a[href*="/order/"], a[href*="o="]')
                        links_data = []
                        for link in link_elements:
                            try:
                                href = link.get_attribute('href')
                                data_testid = link.get_attribute('data-testid')
                                links_data.append({'href': href, 'data-testid': data_testid})
                            except:
                                continue
                    except Exception as e:
                        logger.debug(f"Ошибка при получении ссылок элемента {i+1}: {str(e)}")
                        links_data = []
                    
                    # Теперь извлекаем ID из полученных данных
                    logger.info(f"Извлекаем ID для заказа {i+1}")
                    order_id = extract_order_id_from_attributes(element_attributes, element_text, links_data)
                    
                    if order_id:
                        logger.info(f"✅ Заказ {i+1}: ID найден - {order_id}")
                    else:
                        logger.warning(f"❌ Заказ {i+1}: ID не найден")
                    
                    # Получаем заголовок
                    try:
                        # Ищем заголовок по точному паттерну класса
                        title_element = element.find_element(By.CSS_SELECTOR, 'h3[class*="SubjectAndPriceStyles__SubjectsText"]')
                        title = title_element.text
                        logger.debug(f"Заказ {i+1}: Заголовок - {title[:50]}...")
                    except:
                        title = 'Без названия'
                        logger.warning(f"Заказ {i+1}: Заголовок не найден")
                    
                    # Получаем бюджет
                    try:
                        # Ищем бюджет по точному паттерну класса
                        budget_element = element.find_element(By.CSS_SELECTOR, '[class*="SubjectAndPriceStyles__PriceLine"], [class*="PriceValue"]')
                        budget = budget_element.text
                    except:
                        budget = ''
                    
                    # Получаем имя заказчика
                    try:
                        # Ищем имя клиента по точному паттерну класса
                        client_element = element.find_element(By.CSS_SELECTOR, '[class*="StatusAndClientInfoStyles__Name"]')
                        client_name = client_element.text
                    except:
                        client_name = ''
                    
                    # Получаем локацию
                    try:
                        # Ищем локацию по точному паттерну класса
                        location_element = element.find_element(By.CSS_SELECTOR, '[class*="PrefixText"]')
                        location = location_element.text
                    except:
                        location = 'Не указана'
                    
                    # Получаем дату публикации
                    try:
                        # Ищем дату по точному паттерну класса
                        date_element = element.find_element(By.CSS_SELECTOR, '[class*="Date__DateText"]')
                        date_posted = date_element.text
                    except:
                        date_posted = 'Не указано'
                    
                    # Получаем ссылку на заказ
                    order_link = None
                    if links_data:
                        for link_data in links_data:
                            if link_data.get('href'):
                                order_link = link_data['href']
                                break
                    
                    # Получаем основную информацию
                    try:
                        # Ищем основную информацию по точному паттерну класса
                        main_info_element = element.find_element(By.CSS_SELECTOR, '[class*="SnippetBodyStyles__MainInfo"]')
                        main_info = main_info_element.text
                    except:
                        main_info = ''
                    
                    # Создаем объект заказа
                    order_data = {
                        'id': order_id,
                        'title': title,
                        'budget': budget,
                        'client_name': client_name,
                        'location': location,
                        'date_posted': date_posted,
                        'order_link': order_link,
                        'main_info': main_info,
                        'photos': [],  # Отключаем загрузку фотографий
                        'additional_info': ''
                    }
                    
                    # Проверяем, является ли заказ новым
                    if order_processor.is_new_order(order_id, date_posted):
                        logger.info(f"🆕 Заказ {order_id} - НОВЫЙ!")
                        
                        # Если есть ссылка, получаем дополнительную информацию
                        if order_link:
                            additional_info = await get_additional_info(driver, order_link)
                            order_data.update(additional_info)
                        
                        new_orders.append(order_data)
                        order_processor.mark_order_processed(order_id)
                    else:
                        logger.debug(f"⏭️ Заказ {order_id} - уже обработан или слишком старый")
                        processed_count += 1
                    
                    logger.debug(f"Обработан заказ {i+1}/{len(valid_order_elements)}: {order_data.get('id', 'без ID')}")
                    
                except Exception as e:
                    logger.error(f"Ошибка при обработке данных заказа {i+1}: {str(e)}")
                    continue
                
            except Exception as e:
                logger.error(f"Ошибка при обработке заказа {i+1}: {str(e)}")
                continue
        
        # Итоговая статистика
        logger.info(f"📊 Статистика обработки заказов:")
        logger.info(f"   Всего заказов: {len(valid_order_elements)}")
        logger.info(f"   🆕 Новых: {len(new_orders)}")
        logger.info(f"   ⏭️ Уже обработанных: {processed_count}")
        
        return new_orders
        
    except Exception as e:
        logger.error(f"Ошибка при получении заказов: {str(e)}")
        # Сохраняем скриншот при ошибке
        try:
            driver.save_screenshot('orders_error.png')
        except:
            pass
        return []

def load_excluded_words(filename='excluded_words.txt'):
    """
    Загрузка минус-слов из файла
    Args:
        filename: путь к файлу с минус-словами
    Returns:
        set: множество минус-слов в нижнем регистре
    """
    try:
        excluded_words = set()
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Пропускаем пустые строки и комментарии
                if line and not line.startswith('#'):
                    # Разбиваем строку по запятым, если есть несколько слов
                    words = [word.strip().lower() for word in line.split(',')]
                    excluded_words.update(words)
        logger.info(f"Загружено {len(excluded_words)} минус-слов: {excluded_words}")
        return excluded_words
    except Exception as e:
        logger.error(f"Ошибка при загрузке минус-слов: {str(e)}")
        return set()

async def filter_orders(orders):
    """
    Фильтрация заказов по минус-словам
    Args:
        orders: список заказов для фильтрации
    Returns:
        list: отфильтрованный список заказов
    """
    if not orders:
        logger.info("Нет заказов для фильтрации")
        return []
        
    # Загружаем список исключаемых слов
    excluded_words = load_excluded_words()
    logger.info(f"Загружено {len(excluded_words)} слов для фильтрации")
    
    # Фильтруем заказы
    filtered_orders = []
    for order in orders:
        # Получаем весь текст заказа для проверки
        title = order.get('title', '')
        main_info = order.get('main_info', '')
        additional_info = order.get('additional_info', '')
        budget = order.get('budget', '')
        client_name = order.get('client_name', '')
        
        # Объединяем весь текст заказа
        text_to_check = f"{title} {main_info} {additional_info} {budget} {client_name}".lower()
        
        logger.debug(f"Проверяем заказ {order.get('id', 'без ID')}: {title[:50]}...")
        logger.debug(f"Текст для проверки: {text_to_check[:100]}...")
        
        # Проверяем наличие исключаемых слов
        found_excluded_words = []
        for word in excluded_words:
            if word in text_to_check:
                found_excluded_words.append(word)
        
        if found_excluded_words:
            logger.info(f"Заказ {order.get('id', 'без ID')} отфильтрован по минус-словам: {found_excluded_words}")
            continue
            
        filtered_orders.append(order)
    
    logger.info(f"Отфильтровано {len(orders) - len(filtered_orders)} заказов из {len(orders)}")
    return filtered_orders

class OrderProcessor:
    def __init__(self):
        self.processed_orders_file = Path("processed_orders.json")
        self.processed_orders = self.load_processed_orders()
        self.max_order_age_hours = 2  # Максимальный возраст заказа для обработки
        
    def load_processed_orders(self):
        """Загружает список обработанных заказов из файла"""
        try:
            if self.processed_orders_file.exists():
                with open(self.processed_orders_file, 'r', encoding='utf-8') as f:
                    return set(json.load(f))
            return set()
        except Exception as e:
            logger.error(f"Ошибка при загрузке обработанных заказов: {str(e)}")
            return set()
    
    def save_processed_orders(self):
        """Сохраняет список обработанных заказов в файл"""
        try:
            with open(self.processed_orders_file, 'w', encoding='utf-8') as f:
                json.dump(list(self.processed_orders), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка при сохранении обработанных заказов: {str(e)}")
    
    def is_order_recent(self, date_posted):
        """Проверяет, не слишком ли старый заказ"""
        if not date_posted or date_posted == 'Не указано':
            return False
            
        # Парсим время публикации
        time_patterns = {
            r'(\d+)\s*минут? назад': lambda x: timedelta(minutes=int(x)),
            r'(\d+)\s*часа? назад': lambda x: timedelta(hours=int(x)),
            r'(\d+)\s*дней? назад': lambda x: timedelta(days=int(x)),
            r'сегодня': lambda x: timedelta(hours=24),
            r'вчера': lambda x: timedelta(days=1),
        }
        
        for pattern, time_func in time_patterns.items():
            match = re.search(pattern, date_posted, re.IGNORECASE)
            if match:
                try:
                    time_diff = time_func(match.group(1))
                    return time_diff <= timedelta(hours=self.max_order_age_hours)
                except:
                    continue
        
        # Если не удалось распарсить, считаем заказ старым
        return False
    
    def is_new_order(self, order_id, date_posted):
        """Проверяет, является ли заказ новым"""
        if not order_id:
            return False
            
        # Проверяем по времени
        if not self.is_order_recent(date_posted):
            logger.debug(f"Заказ {order_id} слишком старый: {date_posted}")
            return False
            
        # Проверяем по ID
        if order_id in self.processed_orders:
            logger.debug(f"Заказ {order_id} уже обработан")
            return False
            
        return True
    
    def mark_order_processed(self, order_id):
        """Отмечает заказ как обработанный"""
        if order_id:
            self.processed_orders.add(order_id)
            self.save_processed_orders()
            logger.debug(f"Заказ {order_id} отмечен как обработанный")

# Создаем глобальный экземпляр процессора заказов
order_processor = OrderProcessor() 