"""
Конфигурация бота: загрузка переменных окружения из .env файла.
"""

import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
CHANNEL_LINK: str = os.getenv("CHANNEL_LINK", "")
GOOGLE_SHEET_ID: str = os.getenv("GOOGLE_SHEET_ID", "")
GOOGLE_CREDENTIALS_PATH: str = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
ADMIN_ID: int | None = int(os.getenv("ADMIN_ID")) if os.getenv("ADMIN_ID") else None

# Путь к базе данных
DB_PATH: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "bot_database.db")
