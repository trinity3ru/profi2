"""
Файл: orders.py

Назначение:
    Получение, обработка и фильтрация заказов с Profi.ru, включая извлечение
    дополнительных данных и первичную фильтрацию по плюс-словам.

Основные компоненты:

Функции:
    - async_sleep(min_seconds: float = 0.5, max_seconds: float = 1) -> None:
        Асинхронная задержка для имитации человеческого поведения.

    - get_additional_info(driver, order_link) -> dict:
        Получает дополнительную информацию по заказу со страницы заказа.

    - extract_order_id_from_attributes(element_attributes: dict, element_text: str, links_data: list) -> str | None:
        Извлекает ID заказа по атрибутам элемента и ссылкам.

    - extract_fallback_main_info(element_text: str, title: str) -> str:
        Извлекает описание заказа из текста элемента, если основной блок не найден.

    - log_filter_diagnostics(order: dict, text_to_check: str, matched_words: list[str], order_index: int) -> None:
        Логирует диагностические данные фильтрации для первых заказов.

    - get_order_element_safe(driver, selector: str | None, element_index: int, fallback_element):
        Безопасно возвращает элемент заказа, обновляя его при stale element.

    - get_orders(driver) -> list[dict]:
        Асинхронно получает список новых заказов со страницы.

    - load_included_words(filename: str = INCLUDED_WORDS_FILENAME) -> set[str]:
        Загружает плюс-слова для фильтрации заказов.

    - filter_orders(orders: list[dict]) -> list[dict]:
        Фильтрует заказы по плюс-словам (регистр-независимо).

Классы:
    - OrderProcessor:
        Управляет хранением и дедупликацией обработанных заказов.

Константы:
    - INCLUDED_WORDS_FILENAME: str = "included_words.txt"
        Имя файла со списком плюс-слов.
    - EXCLUDED_WORDS_FILENAME: str = "excluded_words.txt"
        Имя файла со списком минус-слов.
    - FILTER_MODE: str = "exclude"
        Режим фильтрации: "include" (плюс-слова) или "exclude" (минус-слова).
"""

# region Импорты
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException
import logging
import asyncio
from datetime import datetime, timedelta
from config import ORDERS_URL, SELENIUM_IMPLICIT_WAIT, SELENIUM_PAGE_LOAD_TIMEOUT
import re
import json
from pathlib import Path
# endregion

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,  # Изменяем на DEBUG для подробного логирования
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# region Константы
# Имя файла со списком плюс-слов (используется при фильтрации заказов)
INCLUDED_WORDS_FILENAME = 'included_words.txt'
EXCLUDED_WORDS_FILENAME = 'excluded_words.txt'
FILTER_MODE = 'exclude'
ADDITIONAL_INFO_MAX_RETRIES = 2
ADDITIONAL_INFO_RETRY_SLEEP_SECONDS = 1.0
FILTER_DIAGNOSTICS_ENABLED = True
FILTER_DIAGNOSTICS_MAX_ORDERS = 10
FILTER_DIAGNOSTICS_TEXT_LIMIT = 300
# endregion

async def async_sleep(min_seconds=0.5, max_seconds=1):
    """Асинхронная задержка для имитации человеческого поведения"""
    await asyncio.sleep(min_seconds)

# region FUNCTION get_additional_info
# CONTRACT
# Args:
#   - driver: Selenium WebDriver для открытия страницы заказа.
#   - order_link: Ссылка на заказ.
# Returns:
#   - dict: Словарь с ключом 'additional_info'.
# Side Effects:
#   - Переход на страницу заказа и возврат на предыдущую страницу.
# Raises:
#   - None
# Tests:
#   - order_link валиден и контейнер найден: возвращается непустой additional_info.
#   - order_link валиден, но контейнер отсутствует: additional_info = ''.
async def get_additional_info(driver, order_link):
    """
    Получение дополнительной информации о заказе со страницы заказа.
    """
    logger.info("[START_FUNCTION][get_additional_info][BLOCK][init] Запрос доп. информации")
    current_url = None
    for attempt in range(1, ADDITIONAL_INFO_MAX_RETRIES + 1):
        try:
            # Сохраняем текущий URL
            current_url = driver.current_url

            # Увеличиваем таймаут загрузки страницы для карточки заказа
            driver.set_page_load_timeout(SELENIUM_PAGE_LOAD_TIMEOUT)

            # Переходим на страницу заказа
            driver.get(order_link)
            await async_sleep(1)

            # Ищем контейнер с дополнительной информацией
            additional_info = ''
            try:
                info_container = driver.find_element(
                    By.CSS_SELECTOR, '[class*="order-card-additional-info__container"]'
                )
                paragraphs = info_container.find_elements(By.TAG_NAME, 'p')
                additional_info = ' '.join([p.text for p in paragraphs if p.text.strip()])
                logger.info("[get_additional_info][BLOCK][found] Доп. информация получена")
            except Exception as e:
                logger.warning(
                    f"[get_additional_info][BLOCK][not_found] Доп. информация не найдена: {str(e)}"
                )

            # Возвращаемся на предыдущую страницу
            if current_url:
                driver.get(current_url)
                await async_sleep(0.5)

            logger.info("[END_FUNCTION][get_additional_info][BLOCK][success] Завершено успешно")
            return {'additional_info': additional_info}
        except Exception as e:
            logger.error(
                f"[get_additional_info][BLOCK][error] Ошибка получения доп. информации "
                f"(попытка {attempt}/{ADDITIONAL_INFO_MAX_RETRIES}): {str(e)}"
            )
            if current_url:
                try:
                    driver.get(current_url)
                    await async_sleep(0.5)
                except Exception:
                    pass
            if attempt < ADDITIONAL_INFO_MAX_RETRIES:
                await async_sleep(ADDITIONAL_INFO_RETRY_SLEEP_SECONDS)
            else:
                logger.error("[END_FUNCTION][get_additional_info][BLOCK][failed] Все попытки исчерпаны")
                return {'additional_info': ''}
# endregion FUNCTION get_additional_info

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

# region FUNCTION extract_fallback_main_info
# CONTRACT
# Args:
#   - element_text: Полный текст элемента заказа.
#   - title: Заголовок заказа, который нужно исключить из описания.
# Returns:
#   - str: Извлеченное описание или пустая строка.
# Side Effects:
#   - None
# Raises:
#   - None
# Tests:
#   - element_text содержит title и описание: возвращается описание без title.
#   - element_text пустой: возвращается "".
def extract_fallback_main_info(element_text, title):
    """
    Извлекает описание заказа из текста элемента, если основной блок не найден.
    """
    logger.info("[START_FUNCTION][extract_fallback_main_info][BLOCK][init] Fallback описания")
    if not element_text:
        logger.info("[END_FUNCTION][extract_fallback_main_info][BLOCK][empty] Текст элемента пуст")
        return ""

    lines = [line.strip() for line in element_text.splitlines() if line.strip()]
    filtered_lines = []
    for line in lines:
        if title and title in line:
            continue
        filtered_lines.append(line)

    if not filtered_lines:
        logger.info("[END_FUNCTION][extract_fallback_main_info][BLOCK][empty] Нет строк после фильтрации")
        return ""

    result = " ".join(filtered_lines).strip()
    logger.info("[END_FUNCTION][extract_fallback_main_info][BLOCK][result] Fallback описание получено")
    return result
# endregion FUNCTION extract_fallback_main_info

# region FUNCTION log_filter_diagnostics
# CONTRACT
# Args:
#   - order: Словарь заказа для диагностики.
#   - text_to_check: Итоговый текст, по которому идет поиск плюс-слов.
#   - matched_words: Список найденных плюс-слов.
#   - order_index: Индекс заказа в списке фильтрации (1..N).
# Returns:
#   - None
# Side Effects:
#   - Запись диагностических логов.
# Raises:
#   - None
# Tests:
#   - order_index=1 и FILTER_DIAGNOSTICS_ENABLED=True: пишет диагностический лог.
#   - order_index>FILTER_DIAGNOSTICS_MAX_ORDERS: ничего не пишет.
def log_filter_diagnostics(order, text_to_check, matched_words, order_index):
    """
    Логирует диагностические данные фильтрации для первых заказов.
    """
    if not FILTER_DIAGNOSTICS_ENABLED:
        return
    if order_index > FILTER_DIAGNOSTICS_MAX_ORDERS:
        return

    title = order.get('title', '')
    main_info = order.get('main_info', '')
    additional_info = order.get('additional_info', '')
    order_id = order.get('id', 'без ID')

    text_preview = text_to_check[:FILTER_DIAGNOSTICS_TEXT_LIMIT]
    logger.info(
        "[filter_orders][BLOCK][diagnostics] "
        f"Заказ {order_index} | ID={order_id} | "
        f"title='{title[:80]}' | "
        f"main_info='{main_info[:120]}' | "
        f"additional_info='{additional_info[:120]}' | "
        f"matched={matched_words} | "
        f"text_preview='{text_preview}'"
    )
# endregion FUNCTION log_filter_diagnostics

# region FUNCTION get_order_element_safe
# CONTRACT
# Args:
#   - driver: Selenium WebDriver для повторного поиска элементов.
#   - selector: CSS-селектор, по которому изначально были получены элементы заказов.
#   - element_index: Индекс элемента в исходном списке.
#   - fallback_element: Исходный WebElement, который может стать stale.
# Returns:
#   - WebElement | None: Актуальный элемент или None, если восстановить не удалось.
# Side Effects:
#   - Повторный поиск элементов на странице.
# Raises:
#   - None
# Tests:
#   - selector валиден и индекс в диапазоне: возвращается свежий элемент.
#   - selector None или индекс вне диапазона: возвращается None.
def get_order_element_safe(driver, selector, element_index, fallback_element):
    """
    Возвращает актуальный элемент заказа, пытаясь восстановить его при stale element.

    Бизнес-логика: если DOM перерисован, элемент может стать stale, поэтому
    делаем повторный поиск по исходному селектору и индексу.
    """
    logger.info("[START_FUNCTION][get_order_element_safe][BLOCK][init] Проверка элемента заказа")
    try:
        _ = fallback_element.tag_name
        logger.info("[END_FUNCTION][get_order_element_safe][BLOCK][ok] Элемент актуален")
        return fallback_element
    except StaleElementReferenceException:
        logger.warning(
            "[get_order_element_safe][BLOCK][stale] Элемент устарел, пробуем восстановить"
        )
    except Exception as e:
        logger.warning(
            f"[get_order_element_safe][BLOCK][error] Ошибка проверки элемента: {str(e)}"
        )

    if not selector:
        logger.warning(
            "[END_FUNCTION][get_order_element_safe][BLOCK][no_selector] Селектор отсутствует"
        )
        return None

    try:
        elements = driver.find_elements(By.CSS_SELECTOR, selector)
        if element_index < len(elements):
            logger.info("[END_FUNCTION][get_order_element_safe][BLOCK][restored] Элемент восстановлен")
            return elements[element_index]
        logger.warning(
            "[END_FUNCTION][get_order_element_safe][BLOCK][index_out] Индекс вне диапазона"
        )
        return None
    except Exception as e:
        logger.error(
            f"[END_FUNCTION][get_order_element_safe][BLOCK][error] Ошибка восстановления элемента: {str(e)}"
        )
        return None
# endregion FUNCTION get_order_element_safe

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
        # Ищем ссылки на заказы по data-testid (основной способ для новой структуры)
        order_selectors = [
            'a[data-testid*="_order-snippet"]',  # Основной селектор - ссылки с data-testid
            'a[href*="/backoffice/n.php?o="]',    # Альтернативный - по URL
            'div[class*="OrderSnippetStyles__CardContainer"]',  # Fallback - контейнеры
            'div[data-testid="ORDER_SNIPPET"]',   # Fallback - по data-testid контейнера
            'div[class*="OrderSnippetContainerStyles__Container"]'  # Fallback - контейнеры
        ]
        
        max_retries = 3
        retry_count = 0
        order_elements = []
        selected_order_selector = None
        
        while retry_count < max_retries:
            try:
                for selector in order_selectors:
                    try:
                        elements = WebDriverWait(driver, SELENIUM_IMPLICIT_WAIT).until(
                            EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
                        )
                        if elements and len(elements) > 0:
                            order_elements = elements
                            selected_order_selector = selector
                            logger.info(f"Найдены элементы заказов по селектору: {selector} (количество: {len(elements)})")
                            break
                    except TimeoutException:
                        logger.debug(f"Селектор {selector} не нашел элементы, пробуем следующий...")
                        continue
                    except Exception as e:
                        logger.debug(f"Ошибка при поиске по селектору {selector}: {str(e)}")
                        continue
                
                if order_elements:
                    break
                else:
                    raise Exception("Не найдено ни одного элемента заказа")
                    
            except Exception as e:
                retry_count += 1
                logger.warning(f"Попытка {retry_count} получения заказов не удалась: {str(e)}")
                if retry_count < max_retries:
                    await async_sleep(2)  # Увеличиваем задержку перед следующей попыткой
                    # Не обновляем страницу, просто ждем - возможно элементы еще загружаются
                    try:
                        # Прокручиваем страницу вниз для загрузки динамического контента
                        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        await async_sleep(2)
                    except:
                        pass
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
        # Если это ссылки (a), проверяем наличие data-testid или href с параметром o=
        # Если это контейнеры (div), проверяем наличие заголовка и даты
        valid_order_elements = []
        
        for i, element in enumerate(order_elements):
            try:
                tag_name = element.tag_name.lower()
                is_valid = False
                
                # Если это ссылка (a), проверяем наличие data-testid или href
                if tag_name == 'a':
                    data_testid = element.get_attribute('data-testid')
                    href = element.get_attribute('href')
                    
                    # Проверяем, что это ссылка на заказ
                    if data_testid and '_order-snippet' in data_testid:
                        is_valid = True
                        logger.debug(f"Элемент {i+1} (ссылка): Найден data-testid заказа: {data_testid}")
                    elif href and ('/backoffice/n.php?o=' in href or '/order/' in href):
                        is_valid = True
                        logger.debug(f"Элемент {i+1} (ссылка): Найден href заказа: {href}")
                
                # Если это контейнер (div), проверяем наличие заголовка и даты
                elif tag_name == 'div':
                    has_title = False
                    has_date = False
                    
                    try:
                        # Ищем заголовок по точному паттерну класса
                        title_element = element.find_element(By.CSS_SELECTOR, 'h3[class*="SubjectAndPriceStyles__SubjectsText"]')
                        has_title = True
                        logger.debug(f"Элемент {i+1} (контейнер): Найден заголовок заказа")
                    except:
                        logger.debug(f"Элемент {i+1} (контейнер): Заголовок заказа не найден")
                    
                    try:
                        # Ищем дату по точному паттерну класса
                        date_element = element.find_element(By.CSS_SELECTOR, '[class*="Date__DateText"]')
                        has_date = True
                        logger.debug(f"Элемент {i+1} (контейнер): Найдена дата заказа")
                    except:
                        logger.debug(f"Элемент {i+1} (контейнер): Дата заказа не найдена")
                    
                    # Добавляем элемент только если он содержит и заголовок, и дату
                    if has_title and has_date:
                        is_valid = True
                
                if is_valid:
                    valid_order_elements.append((i, element))
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
        
        for i, element_data in enumerate(valid_order_elements):
            try:
                logger.info(f"Обрабатываем заказ {i+1}/{len(valid_order_elements)}")

                element_index, element = element_data
                element = get_order_element_safe(
                    driver=driver,
                    selector=selected_order_selector,
                    element_index=element_index,
                    fallback_element=element
                )
                if element is None:
                    logger.warning(f"Заказ {i+1}: элемент недоступен после обновления DOM")
                    continue
                
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
                        # Если текст пустой и элемент - ссылка, берем текст родительского контейнера
                        if not element_text and element.tag_name.lower() == 'a':
                            try:
                                parent = element.find_element(
                                    By.XPATH,
                                    './ancestor::div[contains(@class, "OrderSnippet") or contains(@class, "SnippetBody")]'
                                )
                                element_text = parent.text
                            except Exception:
                                pass
                        logger.debug(f"Заказ {i+1}: Текст элемента (первые 100 символов): {element_text[:100]}...")
                    except Exception as e:
                        logger.debug(f"Ошибка при получении текста элемента {i+1}: {str(e)}")
                        element_text = ""
                    
                    # Получаем ссылки
                    links_data = []
                    try:
                        # Если элемент сам является ссылкой (a), используем его атрибуты
                        if element.tag_name.lower() == 'a':
                            href = element.get_attribute('href')
                            data_testid = element.get_attribute('data-testid')
                            if href or data_testid:
                                links_data.append({'href': href, 'data-testid': data_testid})
                                logger.debug(f"Элемент {i+1} - ссылка: href={href}, data-testid={data_testid}")
                        else:
                            # Ищем ссылки внутри контейнера
                            link_elements = element.find_elements(By.CSS_SELECTOR, 'a[data-testid*="_order-snippet"], a[href*="/order/"], a[href*="o="], a[href*="/backoffice/n.php"]')
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
                    title = 'Без названия'
                    try:
                        # Если элемент - ссылка, ищем заголовок в родительском контейнере или в самой ссылке
                        if element.tag_name.lower() == 'a':
                            # Пробуем найти заголовок в родительском контейнере
                            try:
                                parent = element.find_element(By.XPATH, './ancestor::div[contains(@class, "OrderSnippet") or contains(@class, "SnippetBody")]')
                                title_element = parent.find_element(By.CSS_SELECTOR, 'h3[class*="SubjectAndPriceStyles__SubjectsText"], h3[class*="SubjectsText"], [class*="SubjectsText"]')
                                title = title_element.text
                            except:
                                # Если не нашли в родителе, пробуем aria-label или текст ссылки
                                try:
                                    aria_label = element.get_attribute('aria-label')
                                    if aria_label:
                                        title = aria_label
                                except:
                                    pass
                        else:
                            # Если элемент - контейнер, ищем заголовок внутри
                            title_element = element.find_element(By.CSS_SELECTOR, 'h3[class*="SubjectAndPriceStyles__SubjectsText"], h3[class*="SubjectsText"], [class*="SubjectsText"]')
                            title = title_element.text
                        
                        if title and title != 'Без названия':
                            logger.debug(f"Заказ {i+1}: Заголовок - {title[:50]}...")
                    except Exception as e:
                        logger.warning(f"Заказ {i+1}: Заголовок не найден: {str(e)}")
                    
                    # Получаем данные заказа (бюджет, имя, локация, дата)
                    # Если элемент - ссылка, ищем данные в родительском контейнере
                    search_container = element
                    if element.tag_name.lower() == 'a':
                        try:
                            # Ищем родительский контейнер заказа
                            search_container = element.find_element(By.XPATH, './ancestor::div[contains(@class, "OrderSnippet") or contains(@class, "SnippetBody") or contains(@data-testid, "ORDERS_BOARD")]')
                        except:
                            # Если не нашли родителя, используем сам элемент
                            pass
                    
                    # Получаем бюджет
                    budget = ''
                    try:
                        budget_element = search_container.find_element(By.CSS_SELECTOR, '[class*="SubjectAndPriceStyles__PriceLine"], [class*="PriceValue"], [class*="Price"]')
                        budget = budget_element.text
                    except:
                        pass
                    
                    # Получаем имя заказчика
                    client_name = ''
                    try:
                        # Пробуем найти по классу
                        client_element = search_container.find_element(By.CSS_SELECTOR, '[class*="StatusAndClientInfoStyles__Name"], [class*="Name"]')
                        client_name = client_element.text
                    except:
                        # Если не нашли по классу, пробуем найти span с текстом через XPath
                        try:
                            client_element = search_container.find_element(By.XPATH, './/span[contains(text(), "Владислав") or contains(text(), "Татьяна") or contains(text(), "Азеке") or contains(text(), "Вероника") or contains(text(), "Наталья")]')
                            client_name = client_element.text
                        except:
                            pass
                    
                    # Получаем локацию
                    location = 'Не указана'
                    try:
                        location_element = search_container.find_element(By.CSS_SELECTOR, '[class*="PrefixText"], [class*="Location"], [aria-label*="Дистанционно"]')
                        location = location_element.text or location_element.get_attribute('aria-label') or 'Не указана'
                    except:
                        pass
                    
                    # Получаем дату публикации
                    date_posted = 'Не указано'
                    try:
                        date_element = search_container.find_element(By.CSS_SELECTOR, '[class*="Date__DateText"], [class*="DateText"], [class*="Date"]')
                        date_posted = date_element.text
                    except:
                        pass
                    
                    # Получаем ссылку на заказ
                    order_link = None
                    if links_data:
                        for link_data in links_data:
                            if link_data.get('href'):
                                order_link = link_data['href']
                                break
                    
                    # Получаем основную информацию
                    main_info = ''
                    try:
                        # Если элемент - ссылка, ищем информацию в родительском контейнере
                        if element.tag_name.lower() == 'a':
                            try:
                                parent = element.find_element(By.XPATH, './ancestor::div[contains(@class, "OrderSnippet") or contains(@class, "SnippetBody")]')
                                main_info_element = parent.find_element(
                                    By.CSS_SELECTOR,
                                    '[class*="SnippetBodyStyles__MainInfo"], [class*="MainInfo"], p[class*="sc-xb0Fq"]'
                                )
                                main_info = main_info_element.text
                            except:
                                pass
                        else:
                            main_info_element = search_container.find_element(
                                By.CSS_SELECTOR,
                                '[class*="SnippetBodyStyles__MainInfo"], [class*="MainInfo"], p[class*="sc-xb0Fq"]'
                            )
                            main_info = main_info_element.text
                    except:
                        pass

                    # Fallback: если не нашли main_info, пробуем извлечь из текста элемента
                    if not main_info and element_text:
                        main_info = extract_fallback_main_info(element_text, title)
                        if main_info:
                            logger.info(f"Заказ {i+1}: Описание получено fallback-методом")
                    
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

# region FUNCTION load_included_words
# CONTRACT
# Args:
#   - filename: Путь к файлу со списком плюс-слов (по одному в строке или через запятую).
# Returns:
#   - set: Множество плюс-слов в нижнем регистре.
# Side Effects:
#   - Чтение файла по пути 'filename'.
# Raises:
#   - Exception: При ошибках чтения файла (логируется и возвращается пустой set).
# Tests:
#   - filename="included_words.txt" с "adwords, Директ": вернет {"adwords", "директ"}.
def load_included_words(filename=INCLUDED_WORDS_FILENAME):
    """
    Загрузка плюс-слов из файла.

    Бизнес-логика: плюс-слова используются для допуска заказа к отправке.
    """
    logger.info("[START_FUNCTION][load_included_words][BLOCK][init] Старт загрузки плюс-слов")
    try:
        included_words = set()
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Пропускаем пустые строки и комментарии для удобства редактирования
                if line and not line.startswith('#'):
                    # Разбиваем строку по запятым, если есть несколько слов
                    words = [word.strip().lower() for word in line.split(',') if word.strip()]
                    included_words.update(words)
        logger.info(
            "[END_FUNCTION][load_included_words][BLOCK][result] "
            f"Загружено {len(included_words)} плюс-слов: {included_words}"
        )
        return included_words
    except Exception as e:
        logger.error(
            "[END_FUNCTION][load_included_words][BLOCK][error] "
            f"Ошибка при загрузке плюс-слов: {str(e)}"
        )
        return set()
# endregion FUNCTION load_included_words

# region FUNCTION load_excluded_words
# CONTRACT
# Args:
#   - filename: Путь к файлу со списком минус-слов (по одному в строке или через запятую).
# Returns:
#   - set: Множество минус-слов в нижнем регистре.
# Side Effects:
#   - Чтение файла по пути 'filename'.
# Raises:
#   - Exception: При ошибках чтения файла (логируется и возвращается пустой set).
# Tests:
#   - filename="excluded_words.txt" с "красоты, маркетплейс": вернет {"красоты", "маркетплейс"}.
def load_excluded_words(filename=EXCLUDED_WORDS_FILENAME):
    """
    Загрузка минус-слов из файла.

    Бизнес-логика: минус-слова используются для исключения заказов.
    """
    logger.info("[START_FUNCTION][load_excluded_words][BLOCK][init] Старт загрузки минус-слов")
    try:
        excluded_words = set()
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    words = [word.strip().lower() for word in line.split(',') if word.strip()]
                    excluded_words.update(words)
        logger.info(
            "[END_FUNCTION][load_excluded_words][BLOCK][result] "
            f"Загружено {len(excluded_words)} минус-слов: {excluded_words}"
        )
        return excluded_words
    except Exception as e:
        logger.error(
            "[END_FUNCTION][load_excluded_words][BLOCK][error] "
            f"Ошибка при загрузке минус-слов: {str(e)}"
        )
        return set()
# endregion FUNCTION load_excluded_words

# region FUNCTION filter_orders
# CONTRACT
# Args:
#   - orders: Список заказов для фильтрации.
# Returns:
#   - list: Список заказов, допущенных по плюс-словам.
# Side Effects:
#   - Чтение файла плюс-слов, запись логов.
# Raises:
#   - None
# Tests:
#   - orders=[{"title":"AdWords аудит","main_info":"","additional_info":""}]: заказ проходит.
#   - orders=[{"title":"Дизайн","main_info":"","additional_info":""}]: заказ отфильтрован.
async def filter_orders(orders):
    """
    Фильтрация заказов по плюс- или минус-словам.

    Бизнес-логика:
        - include: заказ допускается, если найдено любое плюс-слово.
        - exclude: заказ исключается, если найдено любое минус-слово.
    """
    logger.info("[START_FUNCTION][filter_orders][BLOCK][init] Старт фильтрации заказов")
    if not orders:
        logger.info("[END_FUNCTION][filter_orders][BLOCK][empty] Нет заказов для фильтрации")
        return []

    # Загружаем слова в зависимости от режима
    if FILTER_MODE == 'include':
        included_words = load_included_words()
        logger.info(
            f"[filter_orders][BLOCK][config] Загружено {len(included_words)} плюс-слов для фильтрации"
        )
        if not included_words:
            logger.warning(
                "[END_FUNCTION][filter_orders][BLOCK][no_words] Плюс-слова не заданы, заказы не отправляются"
            )
            return []
    else:
        excluded_words = load_excluded_words()
        logger.info(
            f"[filter_orders][BLOCK][config] Загружено {len(excluded_words)} минус-слов для фильтрации"
        )
        if not excluded_words:
            logger.warning(
                "[END_FUNCTION][filter_orders][BLOCK][no_words] Минус-слова не заданы, заказы не фильтруются"
            )
            return orders

    # Фильтруем заказы
    filtered_orders = []
    for order_index, order in enumerate(orders, start=1):
        # Берем только заголовок и описание (без бюджета и имени клиента)
        title = order.get('title', '')
        main_info = order.get('main_info', '')
        additional_info = order.get('additional_info', '')
        description = order.get('description', '')

        # Объединяем текст заголовка и описания для поиска плюс-слов
        text_to_check = f"{title} {main_info} {additional_info} {description}".lower()

        logger.debug(
            f"[filter_orders][BLOCK][order_check] "
            f"Проверяем заказ {order.get('id', 'без ID')}: {title[:50]}..."
        )

        if FILTER_MODE == 'include':
            # Проверяем наличие плюс-слов
            found_included_words = []
            for word in included_words:
                if word in text_to_check:
                    found_included_words.append(word)

            log_filter_diagnostics(order, text_to_check, found_included_words, order_index)

            if not found_included_words:
                logger.info(
                    f"[filter_orders][BLOCK][filtered] Заказ {order.get('id', 'без ID')} "
                    f"отфильтрован по плюс-словам (не найдено совпадений)"
                )
                continue

            logger.info(
                f"[filter_orders][BLOCK][accepted] Заказ {order.get('id', 'без ID')} "
                f"допущен по плюс-словам: {found_included_words}"
            )
            order['matched_included_words'] = found_included_words
            filtered_orders.append(order)
        else:
            # Проверяем наличие минус-слов
            found_excluded_words = []
            for word in excluded_words:
                if word in text_to_check:
                    found_excluded_words.append(word)

            log_filter_diagnostics(order, text_to_check, found_excluded_words, order_index)

            if found_excluded_words:
                logger.info(
                    f"[filter_orders][BLOCK][filtered] Заказ {order.get('id', 'без ID')} "
                    f"отфильтрован по минус-словам: {found_excluded_words}"
                )
                continue

            logger.info(
                f"[filter_orders][BLOCK][accepted] Заказ {order.get('id', 'без ID')} "
                f"допущен (минус-слов не найдено)"
            )
            filtered_orders.append(order)

    logger.info(
        "[END_FUNCTION][filter_orders][BLOCK][result] "
        f"Отфильтровано {len(orders) - len(filtered_orders)} заказов из {len(orders)}"
    )
    return filtered_orders
# endregion FUNCTION filter_orders

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
            # Если дата не указана, считаем заказ новым (чтобы не пропустить)
            logger.debug("Дата публикации не указана, считаем заказ новым")
            return True
            
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
                    if pattern == r'сегодня':
                        time_diff = timedelta(hours=24)
                    elif pattern == r'вчера':
                        time_diff = timedelta(days=1)
                    else:
                        time_diff = time_func(match.group(1))
                    is_recent = time_diff <= timedelta(hours=self.max_order_age_hours)
                    logger.debug(f"Заказ с датой '{date_posted}': разница {time_diff}, новый: {is_recent}")
                    return is_recent
                except Exception as e:
                    logger.debug(f"Ошибка при парсинге даты '{date_posted}' по паттерну '{pattern}': {e}")
                    continue
        
        # Если не удалось распарсить, считаем заказ новым (чтобы не пропустить)
        logger.warning(f"Не удалось распарсить дату '{date_posted}', считаем заказ новым")
        return True
    
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