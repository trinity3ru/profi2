from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Request(Base):
    """Модель для хранения заявок с profi.ru"""
    __tablename__ = 'requests'
    
    id = Column(Integer, primary_key=True)
    request_id = Column(String, unique=True, nullable=False)  # ID заявки на profi.ru
    title = Column(String, nullable=False)  # Заголовок заявки
    description = Column(String)  # Описание заявки
    category = Column(String)  # Категория услуги
    location = Column(String)  # Местоположение
    price = Column(String)  # Цена (если указана)
    created_at = Column(DateTime, default=datetime.utcnow)  # Время создания записи
    is_processed = Column(Boolean, default=False)  # Флаг обработки заявки
    
    def __repr__(self):
        return f"<Request(id={self.request_id}, title='{self.title}')>"
    
    def to_telegram_message(self):
        """Преобразование заявки в текст для отправки в Telegram"""
        return f"""🔔 Новая заявка!
        
📋 {self.title}
📝 {self.description}
🏷 Категория: {self.category}
📍 Локация: {self.location}
💰 Цена: {self.price or 'Не указана'}

🔗 Ссылка: https://profi.ru/backoffice/n/{self.request_id}""" 