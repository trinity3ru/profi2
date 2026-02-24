"""
Конфигурационный файл для парсера Profi.ru
"""
import os
import logging
from dotenv import load_dotenv
from pathlib import Path

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Определяем путь к .env файлу
env_path = Path('.') / '.env'
logger.info(f"Путь к .env файлу: {env_path.absolute()}")

if not env_path.exists():
    raise FileNotFoundError(f"Файл .env не найден по пути: {env_path.absolute()}")

# Загружаем .env файл сразу при импорте модуля
load_dotenv(env_path, override=True)

def reload_config():
    """Перезагрузка конфигурации из .env файла"""
    global TELEGRAM_CHAT_ID, TELEGRAM_BOT_TOKEN, PROFI_LOGIN, PROFI_PASSWORD, PARSE_INTERVAL
    
    # Проверяем существование файла .env
    if not os.path.exists('.env'):
        logger.error("Файл .env не найден!")
        raise FileNotFoundError("Файл .env не найден в корневой директории проекта")
    
    # Загружаем переменные окружения
    load_dotenv(env_path, override=True)
    
    # Проверяем наличие всех необходимых переменных
    required_vars = ['TELEGRAM_CHAT_ID', 'TELEGRAM_BOT_TOKEN', 'PROFI_LOGIN', 'PROFI_PASSWORD']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        logger.error(f"Отсутствуют обязательные переменные в .env: {', '.join(missing_vars)}")
        raise ValueError(f"Отсутствуют обязательные переменные в .env: {', '.join(missing_vars)}")
    
    # Обновляем глобальные переменные
    TELEGRAM_CHAT_ID = get_env_variable('TELEGRAM_CHAT_ID', required=True)
    TELEGRAM_BOT_TOKEN = get_env_variable('TELEGRAM_BOT_TOKEN', required=True)
    PROFI_LOGIN = get_env_variable('PROFI_LOGIN', required=True)
    PROFI_PASSWORD = get_env_variable('PROFI_PASSWORD', required=True)
    PARSE_INTERVAL = int(get_env_variable('PARSE_INTERVAL', '300'))
    
    logger.info(f"Конфигурация перезагружена. TELEGRAM_CHAT_ID: {TELEGRAM_CHAT_ID}")

def get_env_variable(var_name: str, default=None, required=False) -> str:
    """Получение переменной окружения с проверками"""
    value = os.getenv(var_name, default)
    if required and not value:
        raise ValueError(f'Не указана обязательная переменная окружения: {var_name}')
    if value == 'your_bot_token_here':
        raise ValueError(f'Значение {var_name} не было заменено на реальное значение')
    return value

# Настройки для Profi.ru
PROFI_LOGIN = get_env_variable('PROFI_LOGIN', required=True)
PROFI_PASSWORD = get_env_variable('PROFI_PASSWORD', required=True)
 
logger.info("Настройки авторизации загружены")

BASE_URL = 'https://profi.ru'
LOGIN_URL = f'{BASE_URL}/backoffice/?utm_source=profi.ru'
PROFI_LOGIN_URL = LOGIN_URL
ORDERS_URL = f'{BASE_URL}/backoffice/n.php'

# Настройки для Telegram бота
TELEGRAM_BOT_TOKEN = get_env_variable('TELEGRAM_BOT_TOKEN', required=True)
TELEGRAM_CHAT_ID = get_env_variable('TELEGRAM_CHAT_ID', required=True)
logger.info("Настройки Telegram загружены")

# Настройки базы данных
DATABASE_URL = get_env_variable('DATABASE_URL', 'sqlite:///data/requests.db')

# Настройки парсера
PARSE_INTERVAL = int(get_env_variable('PARSE_INTERVAL', '300'))  # 5 минут вместо 15
MAX_RETRIES = 3
REQUEST_TIMEOUT = 30

# Настройки Selenium
SELENIUM_IMPLICIT_WAIT = 5
SELENIUM_PAGE_LOAD_TIMEOUT = 30

# Фильтры для заявок
MIN_BUDGET = int(get_env_variable('MIN_BUDGET', '0'))
EXCLUDED_KEYWORDS = get_env_variable('EXCLUDED_KEYWORDS', '').split(',')
INCLUDED_KEYWORDS = get_env_variable('INCLUDED_KEYWORDS', '').split(',')

# Селекторы для авторизации Profi.ru
# Рабочие селекторы (найдены эмпирически при тестировании)
LOGIN_FIELD_SELECTOR = 'input[data-testid*="login"]'  # Рабочий селектор
PASSWORD_FIELD_SELECTOR = 'input[type="password"]'     # Рабочий селектор
SUBMIT_BUTTON_SELECTOR = 'button[data-testid="enter_with_sms_btn"]'  # Рабочий селектор

# Fallback-селекторы на случай изменения структуры (используются только если основные не работают)
LOGIN_FIELD_FALLBACK = [
    'input[data-testid*="phone"]',
    'input[data-testid*="email"]',
    'input[type="tel"]',
    'input[type="email"]'
]

PASSWORD_FIELD_FALLBACK = [
    'input[data-testid*="password"]',
    'input[name*="password"]'
]

SUBMIT_BUTTON_FALLBACK = [
    'button[data-testid*="submit"]',
    'button[data-testid*="enter"]',
    'button[type="submit"]'
]

# Таймаут ожидания в секундах
REQUEST_TIMEOUT_SECONDS = 20

logger.info("Конфигурация успешно загружена") 