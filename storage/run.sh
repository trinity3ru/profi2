#!/bin/bash

# Переходим в корень проекта
cd "$(dirname "$0")"

# Активируем виртуальное окружение
source venv/bin/activate

# Устанавливаем PYTHONPATH на src/
export PYTHONPATH="$PYTHONPATH:$(pwd)/src"

# Запускаем бот
python src/main.py
