"""
Тестовый скрипт для проверки конфигурации
"""
import os
from dotenv import load_dotenv

def test_env_variables():
    """Проверка наличия всех необходимых переменных окружения"""
    
    # Загружаем .env файл
    load_dotenv()
    
    # Список обязательных переменных
    required_vars = [
        'TELEGRAM_BOT_TOKEN',
        'TELEGRAM_CHAT_ID', 
        'PROFI_LOGIN',
        'PROFI_PASSWORD'
    ]
    
    # Список опциональных переменных
    optional_vars = [
        'PARSE_INTERVAL',
        'DATABASE_URL',
        'MIN_BUDGET',
        'EXCLUDED_KEYWORDS',
        'INCLUDED_KEYWORDS'
    ]
    
    print("=== ПРОВЕРКА КОНФИГУРАЦИИ ===\n")
    
    # Проверяем обязательные переменные
    print("ОБЯЗАТЕЛЬНЫЕ ПЕРЕМЕННЫЕ:")
    missing_required = []
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: {'*' * len(value)} (скрыто)")
        else:
            print(f"❌ {var}: ОТСУТСТВУЕТ")
            missing_required.append(var)
    
    print("\nОПЦИОНАЛЬНЫЕ ПЕРЕМЕННЫЕ:")
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: {value}")
        else:
            print(f"⚠️  {var}: не установлена (будет использовано значение по умолчанию)")
    
    print("\n=== РЕЗУЛЬТАТ ПРОВЕРКИ ===")
    if missing_required:
        print(f"❌ ОШИБКА: Отсутствуют обязательные переменные: {', '.join(missing_required)}")
        print("Добавьте их в файл .env")
        return False
    else:
        print("✅ Все обязательные переменные настроены!")
        return True

if __name__ == "__main__":
    test_env_variables()