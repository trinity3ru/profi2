"""
Файл: auth/auth_service.py

Назначение:
    Сервис авторизации на сайте Profi.ru с использованием Selenium WebDriver.
    Обеспечивает автоматический вход в систему с поддержкой множественных селекторов
    для надежной работы при изменении структуры страницы авторизации.

Основные компоненты:

Классы:
    - AuthService: Основной класс для управления авторизацией.

Функции:
    - type_with_delay(element, text, delay_range=(0.05, 0.1)):
        Ввод текста с задержкой между символами для имитации человеческого ввода.

Методы AuthService:
    - __init__(): Инициализация сервиса авторизации.
    - initialize_driver(): Инициализация веб-драйвера Chrome с настройками.
    - find_element_with_fallback(selectors, by_type, timeout, condition):
        Поиск элемента с использованием нескольких селекторов (fallback-механизм).
    - login(): Выполнение авторизации на сайте profi.ru.
    - close(): Закрытие браузера с обработкой ошибок.
    - get_driver(): Получение экземпляра драйвера.

Зависимости:
    - selenium
    - webdriver-manager
    - loguru
    - config
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from loguru import logger
import time
import random
 

from config import (
    PROFI_LOGIN,
    PROFI_PASSWORD,
    PROFI_LOGIN_URL,
    LOGIN_FIELD_SELECTOR,
    PASSWORD_FIELD_SELECTOR,
    SUBMIT_BUTTON_SELECTOR,
    LOGIN_FIELD_FALLBACK,
    PASSWORD_FIELD_FALLBACK,
    SUBMIT_BUTTON_FALLBACK,
    REQUEST_TIMEOUT_SECONDS
)

# region FUNCTION type_with_delay
def type_with_delay(element, text, delay_range=(0.05, 0.1)):
    """
    Ввод текста с задержкой между символами для имитации человеческого ввода.
    
    Args:
        element: WebElement для ввода текста
        text: Текст для ввода
        delay_range: Диапазон задержки между символами в секундах
    """
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(*delay_range))
# endregion FUNCTION type_with_delay

class AuthService:
    def __init__(self):
        """Инициализация сервиса авторизации"""
        self.driver = None
    
    def find_element_with_fallback(self, selectors, by_type=By.CSS_SELECTOR, timeout=REQUEST_TIMEOUT_SECONDS, condition=EC.presence_of_element_located):
        """
        Поиск элемента с использованием нескольких селекторов (fallback).
        
        Args:
            selectors: Список селекторов для попытки поиска
            by_type: Тип поиска (By.CSS_SELECTOR, By.XPATH и т.д.)
            timeout: Таймаут ожидания в секундах
            condition: Условие ожидания (EC.presence_of_element_located, EC.element_to_be_clickable и т.д.)
        
        Returns:
            WebElement или None, если элемент не найден
        """
        for i, selector in enumerate(selectors):
            try:
                logger.debug(f"Попытка {i+1}/{len(selectors)}: поиск элемента по селектору '{selector}'")
                element = WebDriverWait(self.driver, timeout).until(
                    condition((by_type, selector))
                )
                logger.info(f"Элемент найден по селектору '{selector}'")
                return element
            except TimeoutException:
                logger.debug(f"Элемент не найден по селектору '{selector}', пробуем следующий...")
                continue
        
        logger.error(f"Элемент не найден ни по одному из селекторов: {selectors}")
        return None
    # endregion FUNCTION find_element_with_fallback
        
    # region FUNCTION initialize_driver
    def initialize_driver(self):
        """Инициализация веб-драйвера Chrome с улучшенными настройками"""
        try:
            chrome_options = webdriver.ChromeOptions()
            # Добавляем опции для работы в фоновом режиме
            #chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-plugins')
            chrome_options.add_argument('--disable-images')  # Отключаем загрузку изображений для ускорения
            # ВАЖНО: JavaScript должен быть включен для работы современной страницы авторизации
            # chrome_options.add_argument('--disable-javascript')  # Отключено для работы с новой структурой страницы
            chrome_options.add_argument('--disable-web-security')
            chrome_options.add_argument('--allow-running-insecure-content')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            
            # Дополнительные опции для отключения GPU и ускорения
            chrome_options.add_argument('--disable-software-rasterizer')
            chrome_options.add_argument('--disable-webgl')
            chrome_options.add_argument('--disable-webgl2')
            chrome_options.add_argument('--disable-3d-apis')
            chrome_options.add_argument('--disable-accelerated-2d-canvas')
            chrome_options.add_argument('--disable-accelerated-video-decode')
            chrome_options.add_argument('--disable-accelerated-video-encode')
            chrome_options.add_argument('--disable-gpu-sandbox')
            chrome_options.add_argument('--disable-gpu-compositing')
            chrome_options.add_argument('--disable-gpu-rasterization')
            chrome_options.add_argument('--disable-gpu-memory-buffer-video-frames')
            chrome_options.add_argument('--disable-gpu-memory-buffer-compositor-resources')
            chrome_options.add_argument('--disable-gpu-memory-buffer-video-capture')
            chrome_options.add_argument('--disable-gpu-memory-buffer-scanout')
            chrome_options.add_argument('--disable-gpu-memory-buffer-shared-images')
            chrome_options.add_argument('--disable-gpu-memory-buffer-pool')
            chrome_options.add_argument('--disable-gpu-memory-buffer-software-compositor')
            chrome_options.add_argument('--disable-gpu-memory-buffer-hardware-compositor')
            chrome_options.add_argument('--disable-gpu-memory-buffer-video-encode')
            chrome_options.add_argument('--disable-gpu-memory-buffer-video-decode')
            
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Дополнительные настройки для отключения изображений
            prefs = {
                "profile.managed_default_content_settings.images": 2,  # Отключаем изображения
                "profile.default_content_setting_values.images": 2,    # Отключаем изображения
                "profile.managed_default_content_settings.stylesheets": 2,  # Отключаем CSS
                "profile.managed_default_content_settings.cookies": 1,      # Разрешаем cookies
                "profile.managed_default_content_settings.javascript": 1,   # Разрешаем JavaScript
                "profile.managed_default_content_settings.plugins": 1,      # Разрешаем плагины
                "profile.managed_default_content_settings.popups": 2,       # Блокируем popups
                "profile.managed_default_content_settings.geolocation": 2,  # Блокируем геолокацию
                "profile.managed_default_content_settings.media_stream": 2, # Блокируем медиа
                "profile.managed_default_content_settings.notifications": 2, # Блокируем уведомления
                "profile.managed_default_content_settings.mixed_script": 2, # Блокируем смешанный контент
                "profile.managed_default_content_settings.protocol_handlers": 2, # Блокируем обработчики протоколов
                "profile.managed_default_content_settings.ppapi_broker": 2, # Блокируем PPAPI брокер
                "profile.managed_default_content_settings.automatic_downloads": 2, # Блокируем автозагрузки
                "profile.managed_default_content_settings.midi_sysex": 2, # Блокируем MIDI
                "profile.managed_default_content_settings.push_messaging": 2, # Блокируем push сообщения
                "profile.managed_default_content_settings.ssl_cert_decisions": 2, # Блокируем SSL сертификаты
                "profile.managed_default_content_settings.metro_switch_to_desktop": 2, # Блокируем Metro
                "profile.managed_default_content_settings.protected_media_identifier": 2, # Блокируем защищенный медиа
                "profile.managed_default_content_settings.app_banner": 2, # Блокируем баннеры приложений
                "profile.managed_default_content_settings.site_engagement": 2, # Блокируем вовлеченность сайта
                "profile.managed_default_content_settings.durable_storage": 2, # Блокируем постоянное хранилище
            }
            chrome_options.add_experimental_option("prefs", prefs)
            
            # Увеличиваем таймауты
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.implicitly_wait(REQUEST_TIMEOUT_SECONDS)
            self.driver.set_page_load_timeout(30)
            self.driver.set_script_timeout(30)
            
            # Скрываем признаки автоматизации
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            logger.info("Веб-драйвер успешно инициализирован")
            return True
        except Exception as e:
            logger.error(f"Ошибка при инициализации драйвера: {str(e)}")
            return False
    # endregion FUNCTION initialize_driver
            
    # region FUNCTION login
    def login(self):
        """Выполнение авторизации на сайте profi.ru с улучшенной обработкой ошибок"""
        try:
            if not self.driver:
                if not self.initialize_driver():
                    logger.error("Не удалось инициализировать драйвер")
                    return None
                
            logger.info("Начинаем процесс авторизации")
            self.driver.get(PROFI_LOGIN_URL)
            time.sleep(3)  # Увеличиваем время ожидания загрузки страницы
            
            # Проверяем, что страница загрузилась
            try:
                WebDriverWait(self.driver, 10).until(
                    lambda d: d.execute_script('return document.readyState') == 'complete'
                )
            except TimeoutException:
                logger.error("Страница авторизации не загрузилась")
                return None
            
            # Даем время на выполнение JavaScript и возможное перенаправление
            time.sleep(3)
            
            # Проверяем, не авторизованы ли мы уже (браузер мог запомнить сессию)
            current_url = self.driver.current_url
            logger.info(f"Текущий URL после загрузки: {current_url}")
            
            # Если мы уже на странице заказов, значит авторизация уже прошла
            if "/backoffice/n.php" in current_url or ("/backoffice" in current_url and "n.php" in current_url):
                logger.info("Пользователь уже авторизован (браузер запомнил сессию), пропускаем форму входа")
                return self.driver
            
            # Ждем загрузки формы авторизации (React приложение может загружаться асинхронно)
            logger.info("Ожидание загрузки формы авторизации...")
            try:
                # Ждем появления контейнера формы или любого input на странице
                WebDriverWait(self.driver, 15).until(
                    lambda d: len(d.find_elements(By.TAG_NAME, 'input')) > 0 or 
                              len(d.find_elements(By.CSS_SELECTOR, '[data-testid*="login"], [data-testid*="phone"], [data-testid*="email"]')) > 0 or
                              "/backoffice/n.php" in d.current_url
                )
                # Проверяем URL еще раз после ожидания
                current_url = self.driver.current_url
                if "/backoffice/n.php" in current_url or ("/backoffice" in current_url and "n.php" in current_url):
                    logger.info("Пользователь уже авторизован (после ожидания загрузки формы), пропускаем форму входа")
                    return self.driver
            except TimeoutException:
                logger.warning("Форма авторизации не загрузилась за отведенное время, продолжаем попытки поиска...")
            
            # Ждем появления поля логина (используем рабочий селектор, fallback только если не работает)
            logger.info("Поиск поля логина...")
            login_selectors = [LOGIN_FIELD_SELECTOR]  # Основной рабочий селектор
            if isinstance(LOGIN_FIELD_FALLBACK, list):
                login_selectors.extend(LOGIN_FIELD_FALLBACK)
            else:
                login_selectors.append(LOGIN_FIELD_FALLBACK)
            
            login_field = self.find_element_with_fallback(login_selectors)
            
            if not login_field:
                # Проверяем еще раз - возможно, страница перенаправила нас после загрузки
                time.sleep(2)  # Даем время на возможное перенаправление
                current_url = self.driver.current_url
                logger.info(f"Поле логина не найдено. Проверяем текущий URL: {current_url}")
                
                # Если мы уже на странице заказов, значит авторизация уже прошла
                if "/backoffice/n.php" in current_url or ("/backoffice" in current_url and "n.php" in current_url):
                    logger.info("Пользователь уже авторизован (автоматическое перенаправление), пропускаем форму входа")
                    return self.driver
                
                logger.error("Поле логина не найдено ни по одному из селекторов")
                self.driver.save_screenshot('login_field_error.png')
                # Сохраняем HTML для анализа
                try:
                    with open('login_page_source.html', 'w', encoding='utf-8') as f:
                        f.write(self.driver.page_source)
                    logger.info("HTML страницы сохранен в login_page_source.html для анализа")
                except Exception as e:
                    logger.error(f"Не удалось сохранить HTML: {e}")
                return None
            
            logger.info("Поле логина найдено, вводим данные...")
            type_with_delay(login_field, PROFI_LOGIN)
            time.sleep(1)
            
            # Ввод пароля (используем рабочий селектор, fallback только если не работает)
            logger.info("Поиск поля пароля...")
            password_selectors = [PASSWORD_FIELD_SELECTOR]  # Основной рабочий селектор
            if isinstance(PASSWORD_FIELD_FALLBACK, list):
                password_selectors.extend(PASSWORD_FIELD_FALLBACK)
            else:
                password_selectors.append(PASSWORD_FIELD_FALLBACK)
            
            password_field = self.find_element_with_fallback(password_selectors)
            
            if not password_field:
                logger.error("Поле пароля не найдено ни по одному из селекторов")
                self.driver.save_screenshot('password_field_error.png')
                return None
            
            logger.info("Поле пароля найдено, вводим данные...")
            type_with_delay(password_field, PROFI_PASSWORD)
            time.sleep(1)
            
            # Нажимаем кнопку "Войти" (используем рабочий селектор, fallback только если не работает)
            logger.info("Поиск кнопки входа...")
            button_selectors = [SUBMIT_BUTTON_SELECTOR]  # Основной рабочий селектор
            if isinstance(SUBMIT_BUTTON_FALLBACK, list):
                button_selectors.extend(SUBMIT_BUTTON_FALLBACK)
            else:
                button_selectors.append(SUBMIT_BUTTON_FALLBACK)
            
            continue_button = self.find_element_with_fallback(
                button_selectors,
                condition=EC.element_to_be_clickable
            )
            
            if not continue_button:
                logger.error("Кнопка входа не найдена или не кликабельна")
                self.driver.save_screenshot('submit_button_error.png')
                return None
            
            logger.info("Кнопка входа найдена, нажимаем...")
            # Пробуем несколько способов клика
            try:
                continue_button.click()
            except Exception as e:
                logger.warning(f"Обычный клик не сработал ({e}), пробуем через JavaScript...")
                try:
                    self.driver.execute_script("arguments[0].click();", continue_button)
                except Exception as e2:
                    logger.error(f"JavaScript клик также не сработал: {e2}")
                    return None
            
            time.sleep(5)  # Увеличиваем задержку после нажатия кнопки для загрузки страницы

            # Проверяем успешность авторизации несколькими способами
            logger.info("Проверка успешности авторизации...")
            auth_success = False
            
            # Способ 1: Проверка по URL (самый надежный способ)
            try:
                WebDriverWait(self.driver, REQUEST_TIMEOUT_SECONDS).until(
                    lambda driver: "/backoffice" in driver.current_url and "n.php" in driver.current_url
                )
                logger.info("Авторизация успешна: URL содержит /backoffice/n.php")
                auth_success = True
            except TimeoutException:
                logger.debug("Проверка по URL не прошла, пробуем другие способы...")
            
            # Способ 2: Проверка по заголовку страницы
            if not auth_success:
                try:
                    current_title = self.driver.title
                    logger.debug(f"Текущий заголовок страницы: '{current_title}'")
                    if "Заказы" in current_title or "backoffice" in current_title.lower():
                        logger.info("Авторизация успешна: заголовок страницы подтверждает вход")
                        auth_success = True
                except Exception as e:
                    logger.debug(f"Ошибка при проверке заголовка: {e}")
            
            # Способ 3: Проверка наличия элементов страницы заказов
            if not auth_success:
                try:
                    # Ищем характерные элементы страницы заказов
                    page_loaded = WebDriverWait(self.driver, 5).until(
                        lambda driver: driver.execute_script('return document.readyState') == 'complete'
                    )
                    # Проверяем наличие элементов, характерных для страницы заказов
                    try:
                        # Ищем элементы, которые точно есть на странице заказов
                        self.driver.find_element(By.CSS_SELECTOR, 'body')
                        current_url = self.driver.current_url
                        if "/backoffice" in current_url:
                            logger.info(f"Авторизация успешна: страница загружена, URL: {current_url}")
                            auth_success = True
                    except:
                        pass
                except Exception as e:
                    logger.debug(f"Ошибка при проверке элементов страницы: {e}")
            
            if auth_success:
                logger.info("Авторизация выполнена успешно")
                return self.driver
            else:
                # Сохраняем информацию для диагностики
                current_url = self.driver.current_url
                current_title = self.driver.title
                logger.warning(f"Не удалось подтвердить авторизацию стандартными способами. URL: {current_url}, Title: {current_title}")
                logger.info("Проверяем текущее состояние страницы...")
                
                # Если URL содержит backoffice, считаем авторизацию успешной
                if "/backoffice" in current_url:
                    logger.info("URL содержит /backoffice - считаем авторизацию успешной")
                    return self.driver
                
                if self.driver:
                    self.driver.save_screenshot('auth_error.png')
                return None
                
        except WebDriverException as e:
            logger.error(f"Ошибка WebDriver при авторизации: {e}")
            if self.driver:
                self.driver.save_screenshot('webdriver_error.png')
            return None
        except Exception as e:
            logger.error(f"Неожиданная ошибка при авторизации: {e}")
            if self.driver:
                self.driver.save_screenshot('unexpected_error.png')
            return None
    # endregion FUNCTION login
            
    # region FUNCTION close
    def close(self):
        """Закрытие браузера с обработкой ошибок"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Веб-драйвер успешно закрыт")
            except Exception as e:
                logger.error(f"Ошибка при закрытии драйвера: {str(e)}")
    # endregion FUNCTION close
            
    # region FUNCTION get_driver
    def get_driver(self):
        """Получение экземпляра драйвера"""
        return self.driver
    # endregion FUNCTION get_driver
# endregion Класс AuthService 