from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from loguru import logger

from config import DATABASE_URL
from src.parser.models import Base, Request

class StorageService:
    def __init__(self):
        """Инициализация сервиса хранения"""
        self.engine = create_engine(DATABASE_URL)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        logger.info("Storage service initialized")
        
    def save_request(self, request_data: dict) -> Request:
        """Сохранение новой заявки"""
        try:
            request = Request(**request_data)
            self.session.add(request)
            self.session.commit()
            logger.info(f"Заявка {request.request_id} успешно сохранена")
            return request
        except Exception as e:
            self.session.rollback()
            logger.error(f"Ошибка при сохранении заявки: {str(e)}")
            raise
            
    def get_request_by_id(self, request_id: str) -> Request:
        """Получение заявки по ID"""
        return self.session.query(Request).filter(Request.request_id == request_id).first()
        
    def get_unprocessed_requests(self) -> list[Request]:
        """Получение необработанных заявок"""
        return self.session.query(Request).filter(Request.is_processed == False).all()
        
    def mark_as_processed(self, request_id: str):
        """Отметить заявку как обработанную"""
        request = self.get_request_by_id(request_id)
        if request:
            request.is_processed = True
            self.session.commit()
            logger.info(f"Заявка {request_id} отмечена как обработанная")
            
    def close(self):
        """Закрытие соединения с базой данных"""
        self.session.close()
        logger.info("Storage service connection closed") 