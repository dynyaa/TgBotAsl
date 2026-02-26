"""
Сервис интеграции с Google Sheets.
Экспорт данных о регистрациях в таблицу через service account.
Gracefully обрабатывает отсутствие credentials — логирует warning, не падает.
"""

import logging
import os
from datetime import datetime

import gspread
from google.oauth2.service_account import Credentials

from bot.config import GOOGLE_SHEET_ID, GOOGLE_CREDENTIALS_PATH

logger = logging.getLogger(__name__)

# Области доступа для Google Sheets API
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Глобальный клиент (инициализируется при первом вызове)
_client: gspread.Client | None = None
_initialized: bool = False


def _get_client() -> gspread.Client | None:
    """Получить клиент Google Sheets. Возвращает None, если credentials недоступны."""
    global _client, _initialized

    if _initialized:
        return _client

    _initialized = True

    if not os.path.exists(GOOGLE_CREDENTIALS_PATH):
        logger.warning(
            f"Файл credentials не найден: {GOOGLE_CREDENTIALS_PATH}. "
            "Google Sheets интеграция отключена."
        )
        return None

    if not GOOGLE_SHEET_ID:
        logger.warning("GOOGLE_SHEET_ID не задан. Google Sheets интеграция отключена.")
        return None

    try:
        creds = Credentials.from_service_account_file(
            GOOGLE_CREDENTIALS_PATH, scopes=SCOPES
        )
        _client = gspread.authorize(creds)
        logger.info("Google Sheets клиент успешно инициализирован.")
        return _client
    except Exception as e:
        logger.warning(f"Ошибка инициализации Google Sheets: {e}")
        return None


def _get_or_create_worksheet(
    spreadsheet: gspread.Spreadsheet, title: str, headers: list[str]
) -> gspread.Worksheet:
    """Получить лист по имени или создать новый с заголовками."""
    try:
        worksheet = spreadsheet.worksheet(title)
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=title, rows=1000, cols=len(headers))
        worksheet.append_row(headers, value_input_option="USER_ENTERED")
    return worksheet


async def append_registration(
    first_name: str,
    username: str,
    phone: str,
    email: str,
    webinar_title: str,
    full_name: str = "",
    position: str = "",
) -> bool:
    """
    Добавить строку регистрации в Google Sheets.
    Возвращает True при успехе, False при ошибке.
    """
    client = _get_client()
    if client is None:
        return False

    try:
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)
        headers = ["ФИО", "Имя (Telegram)", "Username", "Телефон", "Email", "Должность", "Вебинар", "Дата регистрации"]
        worksheet = _get_or_create_worksheet(spreadsheet, "Регистрации", headers)

        row = [
            full_name or "",
            first_name or "",
            f"@{username}" if username else "",
            phone or "",
            email or "",
            position or "",
            webinar_title or "",
            datetime.now().strftime("%d.%m.%Y %H:%M"),
        ]
        worksheet.append_row(row, value_input_option="USER_ENTERED")
        logger.info(f"Регистрация добавлена в Google Sheets: {full_name or first_name} на {webinar_title}")
        return True
    except Exception as e:
        logger.warning(f"Ошибка записи в Google Sheets: {e}")
        return False


async def append_contact(
    first_name: str,
    username: str,
    phone: str,
    email: str,
    source: str = "",
) -> bool:
    """
    Добавить контакт (из формы сбора контактов) в Google Sheets.
    Возвращает True при успехе, False при ошибке.
    """
    client = _get_client()
    if client is None:
        return False

    try:
        spreadsheet = client.open_by_key(GOOGLE_SHEET_ID)
        headers = ["Имя", "Username", "Телефон", "Email", "Источник", "Дата"]
        worksheet = _get_or_create_worksheet(spreadsheet, "Контакты", headers)

        row = [
            first_name or "",
            f"@{username}" if username else "",
            phone or "",
            email or "",
            source or "",
            datetime.now().strftime("%d.%m.%Y %H:%M"),
        ]
        worksheet.append_row(row, value_input_option="USER_ENTERED")
        logger.info(f"Контакт добавлен в Google Sheets: {first_name}")
        return True
    except Exception as e:
        logger.warning(f"Ошибка записи контакта в Google Sheets: {e}")
        return False
