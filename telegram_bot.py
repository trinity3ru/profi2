from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)
import logging
from datetime import datetime
import json
import asyncio
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ProfiBot:
    def __init__(self):
        """Инициализация бота"""
        self.is_running = True  # Устанавливаем True по умолчанию для автоматической работы
        
        # Простая инициализация для совместимости без JobQueue
        self.application = (
            Application.builder()
            .token(TELEGRAM_BOT_TOKEN)
            .job_queue(None)  # Отключаем JobQueue для избежания проблем с timezone
            .build()
        )
        
        # Добавляем обработчики команд
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("stop", self.stop_command))
        self.application.add_handler(CommandHandler("filter", self.filter_command))
        self.application.add_handler(CommandHandler("settings", self.settings_command))
        
        # Добавляем обработчик callback-кнопок
        self.application.add_handler(CallbackQueryHandler(self.button_click))
        
        logger.info("Бот успешно инициализирован")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /start"""
        self.is_running = True
        keyboard = [
            [
                InlineKeyboardButton("⏹ Стоп", callback_data='stop'),
                InlineKeyboardButton("⚙️ Настройки", callback_data='settings')
            ],
            [
                InlineKeyboardButton("🔍 Фильтр", callback_data='filter')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            'Бот запущен и готов к работе!\n'
            'Используйте кнопки ниже для управления:',
            reply_markup=reply_markup
        )
        logger.info("Бот запущен через команду start")
    
    async def stop_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /stop"""
        self.is_running = False
        await update.message.reply_text('Бот остановлен. Используйте /start для запуска.')
        logger.info("Бот остановлен через команду stop")
    
    async def filter_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /filter"""
        keyboard = [
            [
                InlineKeyboardButton("💰 Мин. бюджет", callback_data='min_budget'),
                InlineKeyboardButton("📍 Локация", callback_data='location')
            ],
            [
                InlineKeyboardButton("🔙 Назад", callback_data='back_to_main')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            'Настройки фильтров:\n'
            '- Минимальный бюджет\n'
            '- Локация\n'
            'Выберите параметр для настройки:',
            reply_markup=reply_markup
        )
    
    async def settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /settings"""
        keyboard = [
            [
                InlineKeyboardButton("⏰ Время работы", callback_data='work_time'),
                InlineKeyboardButton("⌛️ Интервал", callback_data='interval')
            ],
            [
                InlineKeyboardButton("🔙 Назад", callback_data='back_to_main')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            'Настройки бота:\n'
            '- Время работы (6:00 - 22:00)\n'
            '- Интервал проверки\n'
            'Выберите параметр для настройки:',
            reply_markup=reply_markup
        )
    
    async def button_click(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка нажатий на кнопки"""
        query = update.callback_query
        await query.answer()
        
        if query.data == 'stop':
            self.is_running = False
            await query.edit_message_text('Бот остановлен. Используйте /start для запуска.')
        elif query.data == 'settings':
            await self.settings_command(update, context)
        elif query.data == 'filter':
            await self.filter_command(update, context)
        elif query.data == 'back_to_main':
            await self.start_command(update, context)
    
    def truncate_text(self, text: str, max_length: int = 1000) -> str:
        """
        Обрезает текст до максимальной длины, сохраняя целостность
        Args:
            text: Исходный текст
            max_length: Максимальная длина
        Returns:
            str: Обрезанный текст
        """
        if len(text) <= max_length:
            return text
        
        # Обрезаем до последнего пробела перед лимитом
        truncated = text[:max_length]
        last_space = truncated.rfind(' ')
        
        if last_space > max_length * 0.8:  # Если пробел найден в последних 20%
            return truncated[:last_space] + "..."
        else:
            return truncated + "..."
    
    async def send_order(self, order: dict):
        """
        Отправка информации о заказе в Telegram с улучшенной обработкой ошибок
        Args:
            order (dict): Словарь с информацией о заказе
        """
        # Убираем проверку is_running - она блокирует отправку при автоматической работе
        # if not self.is_running:
        #     logger.info("Бот остановлен, заказ не отправлен")
        #     return
            
        # Формируем базовое сообщение с заголовком
        message_parts = [
            f"*{order.get('title', 'Без названия')}*\n",
        ]
        
        # Добавляем имя заказчика, если есть
        client_name = order.get('client_name', '').strip()
        if client_name:
            message_parts.append(f"👤 {client_name}\n")
        
        # Добавляем описание заказа из поля main_info
        main_info = order.get('main_info', '')
        if main_info:
            # Убираем лишние пробелы и переносы строк
            main_info = ' '.join(main_info.split())
            message_parts.append(f"{main_info}\n")
        
        # Добавляем бюджет, только если он указан и не содержится в заголовке
        budget = order.get('budget', '').strip()
        if budget and budget not in order.get('title', ''):
            message_parts.append(f"💰 {budget}\n")
        
        # Добавляем дополнительную информацию, если есть
        additional_info = order.get('additional_info', '').strip()
        if additional_info:
            # Ограничиваем длину дополнительной информации
            additional_info = self.truncate_text(additional_info, 300)
            message_parts.append(f"\nℹ️ *Дополнительная информация:*\n{additional_info}\n")

        # Добавляем плюс-слова, по которым заказ прошел фильтр
        matched_words = order.get('matched_included_words', [])
        if matched_words:
            words_text = ', '.join(matched_words)
            message_parts.append(f"\n✅ Ключевые слова: {words_text}\n")
        
        # Добавляем локацию и дату публикации
        message_parts.extend([
            f"📍 {order.get('location', 'Не указана')}\n",
            f"⏰ {order.get('date_posted', 'Не указано')}\n",
            f"🔗 [Подробнее]({order.get('order_link', '#')})"
        ])
        
        # Собираем сообщение и ограничиваем его длину
        message = ''.join(message_parts)
        message = self.truncate_text(message, 1000)  # Telegram лимит для caption
        
        try:
            logger.info(f"Попытка отправки заказа в группу с ID: {TELEGRAM_CHAT_ID}")
            
            # Добавляем задержку между отправками для избежания flood control
            await asyncio.sleep(1)
            
            # Отправляем только текстовое сообщение (отключаем фотографии для ускорения)
            # photos = order.get('photos', [])
            # if photos:
            #     logger.info(f"Отправка заказа с фотографией. ID заказа: {order.get('id', 'без ID')}")
            #     await self.application.bot.send_photo(
            #         chat_id=TELEGRAM_CHAT_ID,
            #         photo=photos[0],
            #         caption=message,
            #         parse_mode='Markdown'
            #     )
            #     
            #     # Если есть дополнительные фотографии, отправляем их отдельно с задержкой
            #     if len(photos) > 1:
            #         logger.info(f"Отправка дополнительных фотографий ({len(photos)-1} шт.)")
            #         await asyncio.sleep(2)  # Задержка перед отправкой группы
            #         
            #         # Ограничиваем количество фотографий в группе
            #         remaining_photos = photos[1:6]  # Максимум 5 дополнительных фото
            #         media_group = [
            #             InputMediaPhoto(media=photo)
            #             for photo in remaining_photos
            #         ]
            #         await self.application.bot.send_media_group(
            #             chat_id=TELEGRAM_CHAT_ID,
            #             media=media_group
            #         )
            # else:
            #     # Если фотографий нет, отправляем только текст
            #     logger.info(f"Отправка текстового сообщения. ID заказа: {order.get('id', 'без ID')}")
            #     await self.application.bot.send_message(
            #         chat_id=TELEGRAM_CHAT_ID,
            #         text=message,
            #         parse_mode='Markdown',
            #         disable_web_page_preview=True
            #     )
            
            # Отправляем только текстовое сообщение
            logger.info(f"Отправка текстового сообщения. ID заказа: {order.get('id', 'без ID')}, Chat ID: {TELEGRAM_CHAT_ID}")
            
            # Проверяем, что бот инициализирован
            if not self.application.bot:
                logger.error("Бот не инициализирован, невозможно отправить сообщение")
                return
            
            result = await self.application.bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=message,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            
            logger.info(f"✅ Заказ {order.get('id', 'без ID')} от {order.get('date_posted', 'неизвестной даты')} успешно отправлен в группу {TELEGRAM_CHAT_ID}. Message ID: {result.message_id}")
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Ошибка при отправке заказа {order.get('id', 'без ID')} в группу {TELEGRAM_CHAT_ID}: {error_msg}")
            
            # Обработка специфических ошибок
            if "Flood control exceeded" in error_msg:
                logger.warning("Превышен лимит отправки сообщений, ждем 20 секунд")
                await asyncio.sleep(20)
            elif "Message caption is too long" in error_msg:
                logger.warning("Сообщение слишком длинное, отправляем без caption")
                try:
                    await self.application.bot.send_message(
                        chat_id=TELEGRAM_CHAT_ID,
                        text="📋 Новый заказ (описание слишком длинное)",
                        parse_mode='Markdown'
                    )
                except Exception as e2:
                    logger.error(f"Ошибка при отправке упрощенного сообщения: {str(e2)}")
            elif "Timed out" in error_msg:
                logger.warning("Таймаут при отправке, ждем 10 секунд")
                await asyncio.sleep(10)
    
    async def start(self):
        """Запуск бота"""
        try:
            await self.application.initialize()
            await self.application.start()
            self.is_running = True
            await self.application.updater.start_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True  # Игнорируем старые сообщения
            )
            logger.info("Бот запущен в режиме polling")
        except Exception as e:
            logger.error(f"Ошибка при запуске бота: {str(e)}")
            self.is_running = False
            raise
    
    async def stop(self):
        """Остановка бота"""
        try:
            self.is_running = False
            if hasattr(self.application.updater, 'running') and self.application.updater.running:
                await self.application.updater.stop()
            if hasattr(self.application, 'running') and self.application.running:
                await self.application.stop()
            await self.application.shutdown()
            logger.info("Бот успешно остановлен")
        except Exception as e:
            logger.error(f"Ошибка при остановке бота: {str(e)}")
            raise

if __name__ == "__main__":
    # Тестовый запуск бота
    bot = ProfiBot()
    bot.start() 