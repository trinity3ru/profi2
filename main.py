import logging
import asyncio
from app import ProfiApp

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    app = ProfiApp()
    try:
        asyncio.run(app.run())
    except KeyboardInterrupt:
        logger.info("Программа завершена пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка при запуске: {str(e)}") 