"""
Хендлер команды /start.
Приветствие и показ главного меню (без автоматической регистрации на вебинар).
"""

import logging

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery

from bot.keyboards.inline import main_menu_keyboard
from bot.services.database import create_or_update_user

logger = logging.getLogger(__name__)

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Обработка команды /start — приветствие и главное меню."""
    user = message.from_user
    first_name = user.first_name or "друг"

    # Сохраняем/обновляем пользователя в БД
    await create_or_update_user(
        telegram_id=user.id,
        first_name=first_name,
        username=user.username,
    )

    text = (
        f"Здравствуйте, {first_name}! \U0001f44b\n\n"
        f"Добро пожаловать в бот нашего образовательного центра!\n"
        f"Здесь вы можете записаться на вебинары, узнать о наших программах и мероприятиях.\n\n"
        f"Выберите интересующий раздел:"
    )

    await message.answer(
        text=text,
        reply_markup=main_menu_keyboard(),
    )


@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery) -> None:
    """Возврат в главное меню."""
    await callback.answer()
    user = callback.from_user
    first_name = user.first_name or "друг"

    text = (
        f"{first_name}, вы в главном меню.\n"
        f"Выберите интересующий раздел:"
    )

    await callback.message.edit_text(
        text=text,
        reply_markup=main_menu_keyboard(),
    )
