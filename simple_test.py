import os
from dotenv import load_dotenv

print("=== ПРОСТОЙ ТЕСТ ЗАГРУЗКИ .env ===")

# Загружаем .env файл
load_dotenv()

# Проверяем все переменные
variables = [
    'TELEGRAM_BOT_TOKEN',
    'TELEGRAM_CHAT_ID', 
    'PROFI_LOGIN',
    'PROFI_PASSWORD',
    'PARSE_INTERVAL',
    'DATABASE_URL'
]

print("Проверяем переменные:")
for var in variables:
    value = os.getenv(var)
    if value:
        print(f"✅ {var}: {'*' * min(len(value), 10)} (скрыто)")
    else:
        print(f"❌ {var}: НЕ НАЙДЕНА")

print("\nПроверяем содержимое файла .env:")
try:
    with open('.env', 'r', encoding='utf-8') as f:
        lines = f.readlines()
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if line and not line.startswith('#'):
                if '=' in line:
                    key = line.split('=')[0].strip()
                    print(f"Строка {i}: {key}")
                else:
                    print(f"Строка {i}: {line}")
except Exception as e:
    print(f"Ошибка чтения файла: {e}")