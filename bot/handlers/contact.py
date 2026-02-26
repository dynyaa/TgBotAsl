"""
Хендлер сбора контактных данных (FSM).
Запрашивает телефон (кнопка 'Поделиться контактом' или ввод вручную),
опционально email, сохраняет в БД и Google Sheets.
"""

import logging

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext

from bot.states.forms import ContactForm
from bot.keyboards.inline import skip_email_keyboard, back_to_menu_keyboard
from bot.keyboards.inline import phone_request_keyboard
from bot.services.database import create_or_update_user, get_user
from bot.services.sheets import append_contact

logger = logging.getLogger(__name__)

router = Router()


async def start_contact_collection(
    callback: CallbackQuery,
    state: FSMContext,
    source: str = "",
) -> None:
    """
    Начать процесс сбора контактных данных.
    Вызывается из других хендлеров (menu.py).
    """
    user = callback.from_user

    # Проверяем, есть ли уже телефон у пользователя
    db_user = await get_user(user.id)
    if db_user and db_user.get("phone"):
        await callback.message.answer(
            text=(
                f"\u2705 Спасибо, {user.first_name}!\n\n"
                f"Ваши контактные данные у нас есть.\n"
                f"Менеджер свяжется с вами в ближайшее время.\n\n"
                f"Источник обращения: {source}"
            ),
            reply_markup=ReplyKeyboardRemove(),
        )
        # Повторно экспортируем в Google Sheets
        await append_contact(
            first_name=user.first_name or "",
            username=user.username or "",
            phone=db_user.get("phone", ""),
            email=db_user.get("email", ""),
            source=source,
        )
        return

    # Сохраняем source в state — нужно передать через middleware
    # Отправляем запрос телефона через reply-клавиатуру
    await callback.message.answer(
        text=(
            "\U0001f4f1 Пожалуйста, поделитесь своим номером телефона.\n\n"
            "Нажмите кнопку ниже или введите номер вручную:"
        ),
        reply_markup=phone_request_keyboard(),
    )

    await state.set_state(ContactForm.waiting_for_phone)
    await state.update_data(source=source)


@router.message(ContactForm.waiting_for_phone, F.contact)
async def process_phone_contact(message: Message, state: FSMContext) -> None:
    """Обработка телефона через кнопку 'Поделиться контактом'."""
    phone = message.contact.phone_number
    await _save_phone_and_ask_email(message, state, phone)


@router.message(ContactForm.waiting_for_phone, F.text)
async def process_phone_text(message: Message, state: FSMContext) -> None:
    """Обработка телефона, введённого вручную."""
    text = message.text.strip()

    # Проверка на отмену
    if text == "\u274c Отмена":
        await state.clear()
        await message.answer(
            text="Действие отменено.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    # Простая валидация номера телефона
    phone_clean = text.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if not phone_clean.startswith("+"):
        phone_clean = "+" + phone_clean

    if len(phone_clean) < 10 or not phone_clean[1:].isdigit():
        await message.answer(
            "Пожалуйста, введите корректный номер телефона (например, +7 777 123 4567):"
        )
        return

    await _save_phone_and_ask_email(message, state, phone_clean)


async def _save_phone_and_ask_email(
    message: Message, state: FSMContext, phone: str
) -> None:
    """Сохранить телефон и запросить email."""
    await create_or_update_user(
        telegram_id=message.from_user.id,
        phone=phone,
    )
    await state.update_data(phone=phone)
    await state.set_state(ContactForm.waiting_for_email)

    await message.answer(
        text=(
            "\u2705 Телефон сохранён!\n\n"
            "Укажите ваш email (или нажмите 'Пропустить'):"
        ),
        reply_markup=ReplyKeyboardRemove(),
    )
    # Отправляем inline-кнопку пропуска отдельным сообщением
    await message.answer(
        text="\u2b07\ufe0f",
        reply_markup=skip_email_keyboard(),
    )


@router.message(ContactForm.waiting_for_email, F.text)
async def process_email(message: Message, state: FSMContext) -> None:
    """Обработка email."""
    email = message.text.strip()

    # Простая валидация email
    if "@" not in email or "." not in email:
        await message.answer(
            "Пожалуйста, введите корректный email (например, name@example.com):",
            reply_markup=skip_email_keyboard(),
        )
        return

    await _finish_contact_collection(message, state, email)


@router.callback_query(F.data == "skip_email", ContactForm.waiting_for_email)
async def skip_email(callback: CallbackQuery, state: FSMContext) -> None:
    """Пропуск ввода email."""
    await callback.answer()
    await _finish_contact_collection_callback(callback, state, email=None)


async def _finish_contact_collection(
    message: Message, state: FSMContext, email: str | None
) -> None:
    """Завершить сбор контактов (из Message)."""
    data = await state.get_data()
    phone = data.get("phone", "")
    source = data.get("source", "")
    user = message.from_user

    if email:
        await create_or_update_user(
            telegram_id=user.id,
            email=email,
        )

    # Экспорт в Google Sheets
    await append_contact(
        first_name=user.first_name or "",
        username=user.username or "",
        phone=phone,
        email=email or "",
        source=source,
    )

    await state.clear()

    await message.answer(
        text=(
            f"\u2705 Спасибо, {user.first_name}!\n\n"
            f"Ваши контактные данные сохранены.\n"
            f"Менеджер свяжется с вами в ближайшее время."
        ),
        reply_markup=back_to_menu_keyboard(),
    )


async def _finish_contact_collection_callback(
    callback: CallbackQuery, state: FSMContext, email: str | None
) -> None:
    """Завершить сбор контактов (из CallbackQuery)."""
    data = await state.get_data()
    phone = data.get("phone", "")
    source = data.get("source", "")
    user = callback.from_user

    if email:
        await create_or_update_user(
            telegram_id=user.id,
            email=email,
        )

    # Экспорт в Google Sheets
    await append_contact(
        first_name=user.first_name or "",
        username=user.username or "",
        phone=phone,
        email=email or "",
        source=source,
    )

    await state.clear()

    await callback.message.edit_text(
        text=(
            f"\u2705 Спасибо, {user.first_name}!\n\n"
            f"Ваши контактные данные сохранены.\n"
            f"Менеджер свяжется с вами в ближайшее время."
        ),
        reply_markup=back_to_menu_keyboard(),
    )
