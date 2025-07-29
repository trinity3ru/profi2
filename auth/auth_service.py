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
    REQUEST_TIMEOUT_SECONDS
)

def type_with_delay(element, text, delay_range=(0.05, 0.1)):
        for char in text:
            element.send_keys(char)
            time.sleep(random.uniform(*delay_range))

class AuthService:
    def __init__(self):
        """Инициализация сервиса авторизации"""
        self.driver = None
        
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
            chrome_options.add_argument('--disable-javascript')  # Отключаем JavaScript если не нужен
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

    
        
            
    def login(self):
        """Выполнение авторизации на сайте profi.ru с улучшенной обработкой ошибок"""
        try:
            if not self.driver:
                if not self.initialize_driver():
                    logger.error("Не удалось инициализировать драйвер")
                    return None
                
            logger.info("Начинаем процесс авторизации")
            self.driver.get(PROFI_LOGIN_URL)
            time.sleep(2)  # Увеличиваем время ожидания загрузки страницы
            
            # Проверяем, что страница загрузилась
            try:
                WebDriverWait(self.driver, 10).until(
                    lambda d: d.execute_script('return document.readyState') == 'complete'
                )
            except TimeoutException:
                logger.error("Страница авторизации не загрузилась")
                return None
            
            # Ждем появления поля логина
            try:
                login_field = WebDriverWait(self.driver, REQUEST_TIMEOUT_SECONDS).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, LOGIN_FIELD_SELECTOR))
                )
                type_with_delay(login_field, PROFI_LOGIN)
                time.sleep(1)
            except TimeoutException:
                logger.error("Поле логина не найдено")
                self.driver.save_screenshot('login_field_error.png')
                return None
            
            logger.info("Ждём появления поля пароля") 
            # Ввод пароля
            try:
                password_field = WebDriverWait(self.driver, REQUEST_TIMEOUT_SECONDS).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, PASSWORD_FIELD_SELECTOR))
                )
                type_with_delay(password_field, PROFI_PASSWORD)
                time.sleep(1)
            except TimeoutException:
                logger.error("Поле пароля не найдено")
                self.driver.save_screenshot('password_field_error.png')
                return None
            
            # Нажимаем кнопку "Войти"
            try:
                continue_button = WebDriverWait(self.driver, REQUEST_TIMEOUT_SECONDS).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, SUBMIT_BUTTON_SELECTOR))
                )
                continue_button.click()
                time.sleep(3)  # Увеличиваем задержку после нажатия кнопки
            except TimeoutException:
                logger.error("Кнопка входа не найдена или не кликабельна")
                self.driver.save_screenshot('submit_button_error.png')
                return None

            # Проверяем успешность авторизации по заголовку страницы
            try:
                WebDriverWait(self.driver, REQUEST_TIMEOUT_SECONDS).until(
                    lambda driver: "Заказы" in driver.title
                )
                logger.info("Авторизация выполнена успешно")
                return self.driver
            except TimeoutException:
                logger.error("Не удалось подтвердить успешную авторизацию: страница заказов не загрузилась")
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
            
    def close(self):
        """Закрытие браузера с обработкой ошибок"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Веб-драйвер успешно закрыт")
            except Exception as e:
                logger.error(f"Ошибка при закрытии драйвера: {str(e)}")
            
    def get_driver(self):
        """Получение экземпляра драйвера"""
        return self.driver 