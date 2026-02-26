"""
Главный модуль бота: создание бота, dispatcher, подключение роутеров,
запуск scheduler, инициализация БД.
"""

import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties

from bot.config import BOT_TOKEN
from bot.handlers import start, menu, contact, admin
from bot.services.database import init_db
from bot.services.scheduler import (
    schedule_all_webinars,
    start_scheduler,
    stop_scheduler,
)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Точка входа: настройка и запуск бота."""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN не задан! Укажите токен в .env файле.")
        return

    # Инициализация базы данных
    await init_db()
    logger.info("База данных инициализирована")

    # Создание хранилища состояний (FSM)
    storage = MemoryStorage()

    # Создание бота
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    # Создание dispatcher
    dp = Dispatcher(storage=storage)

    # Подключение роутеров (порядок важен: admin перед menu,
    # чтобы admin callback-и обрабатывались первыми)
    dp.include_router(admin.router)
    dp.include_router(start.router)
    dp.include_router(contact.router)
    dp.include_router(menu.router)

    # Запуск планировщика
    start_scheduler()

    # Планирование напоминаний для всех активных вебинаров
    await schedule_all_webinars(bot)

    logger.info("Бот запущен и готов к работе")

    # Запуск polling
    logger.info("Запуск бота в режиме polling...")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        stop_scheduler()
        await bot.session.close()
        logger.info("Бот остановлен")
