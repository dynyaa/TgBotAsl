"""
Сервис базы данных: создание таблиц, CRUD-операции для пользователей,
вебинаров, программ, регистраций и информации о центре.
"""

import aiosqlite
from datetime import datetime
from bot.config import DB_PATH, CHANNEL_LINK


async def init_db() -> None:
    """Создание всех таблиц при первом запуске."""
    async with aiosqlite.connect(DB_PATH) as db:
        # Таблица пользователей
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                first_name TEXT,
                username TEXT,
                phone TEXT,
                email TEXT,
                full_name TEXT,
                position TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)

        # Таблица вебинаров
        await db.execute("""
            CREATE TABLE IF NOT EXISTS webinars (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                timezone TEXT DEFAULT 'Астана',
                link TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)

        # Таблица программ
        await db.execute("""
            CREATE TABLE IF NOT EXISTS programs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                target_audience TEXT,
                result TEXT,
                duration TEXT,
                format TEXT,
                is_active INTEGER DEFAULT 1
            )
        """)

        # Таблица регистраций на вебинары
        await db.execute("""
            CREATE TABLE IF NOT EXISTS registrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                webinar_id INTEGER NOT NULL,
                registered_at TEXT DEFAULT (datetime('now')),
                reminder_1day_sent INTEGER DEFAULT 0,
                reminder_1hour_sent INTEGER DEFAULT 0,
                link_sent INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(telegram_id),
                FOREIGN KEY (webinar_id) REFERENCES webinars(id)
            )
        """)

        # Таблица информации о центре (одна запись)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS center_info (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                text TEXT NOT NULL
            )
        """)

        # Вставляем дефолтный текст о центре, если его нет
        await db.execute("""
            INSERT OR IGNORE INTO center_info (id, text) VALUES (1,
            'Наш образовательный центр — это площадка для профессионального развития и обучения.

Мы проводим:
• Вебинары и онлайн-курсы
• Программы повышения квалификации
• Мастер-классы от практиков

Наша миссия — давать актуальные знания и практические навыки, которые помогут вам расти в карьере и бизнесе.')
        """)

        # Таблица настроек (ключ-значение)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        # Дефолтные значения настроек при первом запуске
        default_settings = {
            "manager_contact": "",
            "channel_link": CHANNEL_LINK,
            "materials_file_id": "",
            "materials_link": "",
            "materials_text": "Вот подборка полезных материалов по теме обучения:",
        }
        for key, value in default_settings.items():
            await db.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                (key, value),
            )

        await db.commit()


# === Пользователи ===

async def get_user(telegram_id: int) -> dict | None:
    """Получить пользователя по telegram_id."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def create_or_update_user(
    telegram_id: int,
    first_name: str | None = None,
    username: str | None = None,
    phone: str | None = None,
    email: str | None = None,
    full_name: str | None = None,
    position: str | None = None,
) -> None:
    """Создать или обновить пользователя."""
    async with aiosqlite.connect(DB_PATH) as db:
        existing = await get_user(telegram_id)
        if existing:
            # Обновляем только переданные поля
            updates = []
            values = []
            for field, value in [
                ("first_name", first_name),
                ("username", username),
                ("phone", phone),
                ("email", email),
                ("full_name", full_name),
                ("position", position),
            ]:
                if value is not None:
                    updates.append(f"{field} = ?")
                    values.append(value)
            if updates:
                values.append(telegram_id)
                await db.execute(
                    f"UPDATE users SET {', '.join(updates)} WHERE telegram_id = ?",
                    values,
                )
                await db.commit()
        else:
            await db.execute(
                "INSERT INTO users (telegram_id, first_name, username, phone, email, full_name, position) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (telegram_id, first_name, username, phone, email, full_name, position),
            )
            await db.commit()


# === Вебинары ===

async def get_active_webinar() -> dict | None:
    """Получить текущий активный вебинар (последний добавленный активный)."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM webinars WHERE is_active = 1 ORDER BY id DESC LIMIT 1"
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_all_active_webinars() -> list[dict]:
    """Получить все активные вебинары."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM webinars WHERE is_active = 1 ORDER BY date, time"
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_webinar_by_id(webinar_id: int) -> dict | None:
    """Получить вебинар по ID."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM webinars WHERE id = ?", (webinar_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def create_webinar(
    title: str, date: str, time: str, timezone: str = "Астана", link: str = ""
) -> int:
    """Создать вебинар, вернуть его ID."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO webinars (title, date, time, timezone, link) VALUES (?, ?, ?, ?, ?)",
            (title, date, time, timezone, link),
        )
        await db.commit()
        return cursor.lastrowid


async def update_webinar(webinar_id: int, **kwargs) -> None:
    """Обновить поля вебинара."""
    async with aiosqlite.connect(DB_PATH) as db:
        updates = []
        values = []
        for key, value in kwargs.items():
            if key in ("title", "date", "time", "timezone", "link", "is_active"):
                updates.append(f"{key} = ?")
                values.append(value)
        if updates:
            values.append(webinar_id)
            await db.execute(
                f"UPDATE webinars SET {', '.join(updates)} WHERE id = ?", values
            )
            await db.commit()


async def delete_webinar(webinar_id: int) -> None:
    """Удалить вебинар и связанные регистрации."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM registrations WHERE webinar_id = ?", (webinar_id,))
        await db.execute("DELETE FROM webinars WHERE id = ?", (webinar_id,))
        await db.commit()


# === Программы ===

async def get_all_active_programs() -> list[dict]:
    """Получить все активные программы."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM programs WHERE is_active = 1 ORDER BY id"
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_program_by_id(program_id: int) -> dict | None:
    """Получить программу по ID."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM programs WHERE id = ?", (program_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None


async def create_program(
    name: str,
    target_audience: str = "",
    result: str = "",
    duration: str = "",
    fmt: str = "",
) -> int:
    """Создать программу, вернуть её ID."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO programs (name, target_audience, result, duration, format) VALUES (?, ?, ?, ?, ?)",
            (name, target_audience, result, duration, fmt),
        )
        await db.commit()
        return cursor.lastrowid


async def update_program(program_id: int, **kwargs) -> None:
    """Обновить поля программы."""
    async with aiosqlite.connect(DB_PATH) as db:
        updates = []
        values = []
        field_map = {
            "name": "name",
            "target_audience": "target_audience",
            "result": "result",
            "duration": "duration",
            "format": "format",
            "is_active": "is_active",
        }
        for key, value in kwargs.items():
            if key in field_map:
                updates.append(f"{field_map[key]} = ?")
                values.append(value)
        if updates:
            values.append(program_id)
            await db.execute(
                f"UPDATE programs SET {', '.join(updates)} WHERE id = ?", values
            )
            await db.commit()


async def delete_program(program_id: int) -> None:
    """Удалить программу."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM programs WHERE id = ?", (program_id,))
        await db.commit()


# === Регистрации ===

async def register_user_for_webinar(user_id: int, webinar_id: int) -> bool:
    """Зарегистрировать пользователя на вебинар. Возвращает False, если уже зарегистрирован."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT id FROM registrations WHERE user_id = ? AND webinar_id = ?",
            (user_id, webinar_id),
        )
        if await cursor.fetchone():
            return False
        await db.execute(
            "INSERT INTO registrations (user_id, webinar_id) VALUES (?, ?)",
            (user_id, webinar_id),
        )
        await db.commit()
        return True


async def get_registrations_for_webinar(webinar_id: int) -> list[dict]:
    """Получить все регистрации для вебинара с данными пользователя."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT r.*, u.first_name, u.username, u.phone, u.email, u.full_name, u.position
            FROM registrations r
            JOIN users u ON r.user_id = u.telegram_id
            WHERE r.webinar_id = ?
            ORDER BY r.registered_at
            """,
            (webinar_id,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_pending_reminders_1day(webinar_id: int) -> list[dict]:
    """Получить регистрации, которым не отправлено напоминание за 1 день."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM registrations WHERE webinar_id = ? AND reminder_1day_sent = 0",
            (webinar_id,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def get_pending_reminders_1hour(webinar_id: int) -> list[dict]:
    """Получить регистрации, которым не отправлено напоминание за 1 час."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM registrations WHERE webinar_id = ? AND reminder_1hour_sent = 0",
            (webinar_id,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def mark_reminder_1day_sent(registration_id: int) -> None:
    """Отметить напоминание за 1 день как отправленное."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE registrations SET reminder_1day_sent = 1 WHERE id = ?",
            (registration_id,),
        )
        await db.commit()


async def mark_reminder_1hour_sent(registration_id: int) -> None:
    """Отметить напоминание за 1 час как отправленное."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE registrations SET reminder_1hour_sent = 1 WHERE id = ?",
            (registration_id,),
        )
        await db.commit()


async def mark_link_sent(registration_id: int) -> None:
    """Отметить ссылку как отправленную."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE registrations SET link_sent = 1 WHERE id = ?",
            (registration_id,),
        )
        await db.commit()


# === Информация о центре ===

async def get_center_info() -> str:
    """Получить текст о центре."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT text FROM center_info WHERE id = 1")
        row = await cursor.fetchone()
        return row[0] if row else "Информация о центре пока не добавлена."


async def update_center_info(text: str) -> None:
    """Обновить текст о центре."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO center_info (id, text) VALUES (1, ?)", (text,)
        )
        await db.commit()


# === Настройки ===


async def get_setting(key: str) -> str | None:
    """Получить значение настройки по ключу."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        )
        row = await cursor.fetchone()
        return row[0] if row else None


async def set_setting(key: str, value: str) -> None:
    """Установить значение настройки."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, value),
        )
        await db.commit()


async def get_all_settings() -> dict[str, str]:
    """Получить все настройки в виде словаря."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT key, value FROM settings")
        rows = await cursor.fetchall()
        return {row[0]: row[1] for row in rows}
