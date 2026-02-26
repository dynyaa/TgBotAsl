"""
Сервис планировщика напоминаний.
Использует APScheduler для отправки напоминаний за 1 день и 1 час до вебинара,
а также для отправки ссылки и приглашения в канал.
"""

import logging
from datetime import datetime, timedelta

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot.config import CHANNEL_LINK
from bot.services.database import (
    get_all_active_webinars,
    get_pending_reminders_1day,
    get_pending_reminders_1hour,
    mark_reminder_1day_sent,
    mark_reminder_1hour_sent,
    mark_link_sent,
    get_setting,
)

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def send_reminder_1day(bot: Bot, webinar: dict) -> None:
    """Отправить напоминание за 1 день до вебинара."""
    registrations = await get_pending_reminders_1day(webinar["id"])
    if not registrations:
        return

    text = (
        f"Напоминаем: завтра состоится вебинар «{webinar['title']}».\n"
        f"Дата/время: {webinar['date']} в {webinar['time']}.\n"
        f"Ссылку на эфир пришлем за 1 час до начала \u2705"
    )

    for reg in registrations:
        try:
            await bot.send_message(chat_id=reg["user_id"], text=text)
            await mark_reminder_1day_sent(reg["id"])
            logger.info(f"Напоминание (1 день) отправлено пользователю {reg['user_id']}")
        except Exception as e:
            logger.warning(
                f"Не удалось отправить напоминание (1 день) пользователю {reg['user_id']}: {e}"
            )


async def send_reminder_1hour(bot: Bot, webinar: dict) -> None:
    """Отправить напоминание за 1 час до вебинара со ссылкой."""
    registrations = await get_pending_reminders_1hour(webinar["id"])
    if not registrations:
        return

    link_text = webinar.get("link") or "Ссылка будет добавлена организатором"
    text = (
        f"Уже через 1 час стартует вебинар «{webinar['title']}».\n"
        f"Вот ваша ссылка для входа: {link_text}\n"
        f"До встречи на эфире! \U0001f525"
    )

    for reg in registrations:
        try:
            await bot.send_message(chat_id=reg["user_id"], text=text)
            await mark_reminder_1hour_sent(reg["id"])
            await mark_link_sent(reg["id"])
            logger.info(f"Напоминание (1 час) + ссылка отправлены пользователю {reg['user_id']}")

            # Планируем отправку приглашения в канал через 5 минут
            run_time = datetime.now() + timedelta(minutes=5)
            scheduler.add_job(
                send_channel_invite,
                "date",
                run_date=run_time,
                args=[bot, reg["user_id"]],
                id=f"channel_invite_{reg['user_id']}_{webinar['id']}",
                replace_existing=True,
            )
        except Exception as e:
            logger.warning(
                f"Не удалось отправить напоминание (1 час) пользователю {reg['user_id']}: {e}"
            )


async def send_channel_invite(bot: Bot, user_id: int) -> None:
    """Отправить приглашение в канал через 5 минут после ссылки на вебинар."""
    # Получаем ссылку на канал из настроек с fallback на .env
    channel_link = await get_setting("channel_link") or CHANNEL_LINK

    text = (
        "Чтобы получать полезные материалы, разборы и бонусы \u2014 "
        "переходите в наш канал \u2705\n"
        "Там мы регулярно публикуем практические советы и кейсы по теме обучения."
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="\u27a1\ufe0f Перейти в канал",
                    url=channel_link,
                )
            ],
            [
                InlineKeyboardButton(
                    text="\U0001f4e9 Получить подборку материалов",
                    callback_data="request_materials",
                )
            ],
            [
                InlineKeyboardButton(
                    text="\U0001f91d Связаться с менеджером",
                    callback_data="contact_manager",
                )
            ],
        ]
    )

    try:
        await bot.send_message(chat_id=user_id, text=text, reply_markup=keyboard)
        logger.info(f"Приглашение в канал отправлено пользователю {user_id}")
    except Exception as e:
        logger.warning(
            f"Не удалось отправить приглашение в канал пользователю {user_id}: {e}"
        )


def _parse_webinar_datetime(webinar: dict) -> datetime | None:
    """Преобразовать дату и время вебинара в объект datetime."""
    try:
        date_str = webinar["date"]
        time_str = webinar["time"]
        # Поддерживаем форматы: DD.MM.YYYY и YYYY-MM-DD
        for fmt in ("%d.%m.%Y %H:%M", "%Y-%m-%d %H:%M", "%d.%m.%Y %H.%M", "%Y-%m-%d %H.%M"):
            try:
                return datetime.strptime(f"{date_str} {time_str}", fmt)
            except ValueError:
                continue
        logger.warning(f"Не удалось распарсить дату/время вебинара: {date_str} {time_str}")
        return None
    except Exception as e:
        logger.warning(f"Ошибка парсинга даты вебинара: {e}")
        return None


async def schedule_webinar_reminders(bot: Bot, webinar: dict) -> None:
    """Запланировать напоминания для конкретного вебинара."""
    webinar_dt = _parse_webinar_datetime(webinar)
    if webinar_dt is None:
        return

    now = datetime.now()
    webinar_id = webinar["id"]

    # Напоминание за 1 день
    reminder_1day_time = webinar_dt - timedelta(days=1)
    if reminder_1day_time > now:
        scheduler.add_job(
            send_reminder_1day,
            "date",
            run_date=reminder_1day_time,
            args=[bot, webinar],
            id=f"reminder_1day_{webinar_id}",
            replace_existing=True,
        )
        logger.info(
            f"Напоминание (1 день) запланировано для вебинара '{webinar['title']}' "
            f"на {reminder_1day_time}"
        )

    # Напоминание за 1 час + ссылка
    reminder_1hour_time = webinar_dt - timedelta(hours=1)
    if reminder_1hour_time > now:
        scheduler.add_job(
            send_reminder_1hour,
            "date",
            run_date=reminder_1hour_time,
            args=[bot, webinar],
            id=f"reminder_1hour_{webinar_id}",
            replace_existing=True,
        )
        logger.info(
            f"Напоминание (1 час) запланировано для вебинара '{webinar['title']}' "
            f"на {reminder_1hour_time}"
        )


async def schedule_all_webinars(bot: Bot) -> None:
    """При запуске бота — запланировать напоминания для всех активных вебинаров."""
    webinars = await get_all_active_webinars()
    for webinar in webinars:
        await schedule_webinar_reminders(bot, webinar)
    logger.info(f"Запланированы напоминания для {len(webinars)} активных вебинаров")


def start_scheduler() -> None:
    """Запустить планировщик."""
    if not scheduler.running:
        scheduler.start()
        logger.info("Планировщик запущен")


def stop_scheduler() -> None:
    """Остановить планировщик."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Планировщик остановлен")
