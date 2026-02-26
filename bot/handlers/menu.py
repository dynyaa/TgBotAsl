"""
Хендлеры меню: Вебинары (просмотр, регистрация с анкетой),
О центре, Программы, детали программ, запрос материалов.
"""

import logging

from aiogram import Router, F
from aiogram.types import (
    CallbackQuery,
    Message,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardRemove,
)
from aiogram.fsm.context import FSMContext

from bot.keyboards.inline import (
    about_center_keyboard,
    programs_list_keyboard,
    program_detail_keyboard,
    back_to_menu_keyboard,
    webinars_list_keyboard,
    webinar_detail_keyboard,
    post_registration_keyboard,
    phone_request_keyboard,
)
from bot.states.forms import WebinarRegistrationForm
from bot.services.database import (
    get_center_info,
    get_all_active_programs,
    get_all_active_webinars,
    get_webinar_by_id,
    get_program_by_id,
    get_setting,
    create_or_update_user,
    register_user_for_webinar,
    get_user,
)
from bot.services.sheets import append_registration

logger = logging.getLogger(__name__)

router = Router()


# ========================================
# ВЕБИНАРЫ (пользовательская часть)
# ========================================


@router.callback_query(F.data == "webinars")
async def show_webinars(callback: CallbackQuery) -> None:
    """Показать список активных вебинаров."""
    await callback.answer()
    webinars = await get_all_active_webinars()

    if not webinars:
        await callback.message.edit_text(
            text="На данный момент нет запланированных вебинаров.\nСледите за обновлениями!",
            reply_markup=back_to_menu_keyboard(),
        )
        return

    text = "\U0001f4c5 <b>Предстоящие вебинары</b>\n\nВыберите вебинар для подробной информации:"
    await callback.message.edit_text(
        text=text,
        reply_markup=webinars_list_keyboard(webinars),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("webinar_detail_"))
async def show_webinar_detail(callback: CallbackQuery) -> None:
    """Показать детали вебинара."""
    await callback.answer()
    webinar_id = int(callback.data.split("_")[-1])
    webinar = await get_webinar_by_id(webinar_id)

    if not webinar or not webinar["is_active"]:
        await callback.message.edit_text(
            text="Вебинар не найден или уже не активен.",
            reply_markup=back_to_menu_keyboard(),
        )
        return

    text = (
        f"\U0001f4e2 <b>{webinar['title']}</b>\n\n"
        f"\U0001f4c5 Дата: {webinar['date']}\n"
        f"\u23f0 Время: {webinar['time']} (по {webinar['timezone']})\n"
    )
    if webinar.get("link"):
        text += f"\U0001f517 Ссылка будет отправлена после регистрации\n"

    text += "\nНажмите «Записаться», чтобы зарегистрироваться на вебинар."

    await callback.message.edit_text(
        text=text,
        reply_markup=webinar_detail_keyboard(webinar_id),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("register_webinar_"))
async def register_for_webinar(callback: CallbackQuery, state: FSMContext) -> None:
    """Начало регистрации на вебинар — запуск FSM анкеты."""
    await callback.answer()
    webinar_id = int(callback.data.split("_")[-1])
    webinar = await get_webinar_by_id(webinar_id)

    if not webinar or not webinar["is_active"]:
        await callback.message.edit_text(
            text="Вебинар не найден или уже не активен.",
            reply_markup=back_to_menu_keyboard(),
        )
        return

    # Проверяем, не зарегистрирован ли уже
    user = callback.from_user
    is_new = await register_user_for_webinar(user.id, webinar_id)
    if not is_new:
        await callback.message.edit_text(
            text=(
                f"\u2139\ufe0f Вы уже зарегистрированы на вебинар «{webinar['title']}»!\n\n"
                f"\U0001f4c5 Дата: {webinar['date']}\n"
                f"\u23f0 Время: {webinar['time']} (по {webinar['timezone']})\n\n"
                f"Мы напомним вам о вебинаре!"
            ),
            reply_markup=post_registration_keyboard(),
            parse_mode="HTML",
        )
        return

    # Сохраняем webinar_id в state и начинаем анкету
    await state.update_data(webinar_id=webinar_id)
    await state.set_state(WebinarRegistrationForm.waiting_for_full_name)

    await callback.message.edit_text(
        text=(
            f"Отлично! Для регистрации на вебинар «{webinar['title']}» "
            f"заполните небольшую анкету.\n\n"
            f"<b>Шаг 1/3</b>\n"
            f"Как вас зовут? (ФИО)"
        ),
        parse_mode="HTML",
    )


# --- FSM: Сбор ФИО ---


@router.message(WebinarRegistrationForm.waiting_for_full_name, F.text)
async def process_full_name(message: Message, state: FSMContext) -> None:
    """Получить ФИО и запросить телефон."""
    full_name = message.text.strip()
    if len(full_name) < 2:
        await message.answer("Пожалуйста, введите ваше ФИО (минимум 2 символа):")
        return

    await state.update_data(full_name=full_name)
    await state.set_state(WebinarRegistrationForm.waiting_for_phone)

    await message.answer(
        text=(
            "\u2705 Спасибо!\n\n"
            "<b>Шаг 2/3</b>\n"
            "\U0001f4f1 Ваш номер телефона?\n\n"
            "Нажмите кнопку ниже или введите номер вручную:"
        ),
        reply_markup=phone_request_keyboard(),
        parse_mode="HTML",
    )


# --- FSM: Сбор телефона ---


@router.message(WebinarRegistrationForm.waiting_for_phone, F.contact)
async def process_reg_phone_contact(message: Message, state: FSMContext) -> None:
    """Обработка телефона через кнопку 'Поделиться контактом'."""
    phone = message.contact.phone_number
    await _save_phone_and_ask_position(message, state, phone)


@router.message(WebinarRegistrationForm.waiting_for_phone, F.text)
async def process_reg_phone_text(message: Message, state: FSMContext) -> None:
    """Обработка телефона, введённого вручную."""
    text = message.text.strip()

    # Проверка на отмену
    if text == "\u274c Отмена":
        await state.clear()
        await message.answer(
            text="Регистрация отменена.",
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

    await _save_phone_and_ask_position(message, state, phone_clean)


async def _save_phone_and_ask_position(
    message: Message, state: FSMContext, phone: str
) -> None:
    """Сохранить телефон и запросить должность."""
    await state.update_data(phone=phone)
    await state.set_state(WebinarRegistrationForm.waiting_for_position)

    await message.answer(
        text=(
            "\u2705 Телефон сохранён!\n\n"
            "<b>Шаг 3/3</b>\n"
            "Кем вы работаете? (должность/сфера деятельности)"
        ),
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML",
    )


# --- FSM: Сбор должности ---


@router.message(WebinarRegistrationForm.waiting_for_position, F.text)
async def process_position(message: Message, state: FSMContext) -> None:
    """Получить должность и завершить регистрацию."""
    position = message.text.strip()
    if len(position) < 2:
        await message.answer("Пожалуйста, укажите вашу должность или сферу деятельности:")
        return

    data = await state.get_data()
    full_name = data["full_name"]
    phone = data["phone"]
    webinar_id = data["webinar_id"]
    user = message.from_user

    # Сохраняем данные в БД
    await create_or_update_user(
        telegram_id=user.id,
        full_name=full_name,
        phone=phone,
        position=position,
    )

    # Получаем данные вебинара
    webinar = await get_webinar_by_id(webinar_id)

    if not webinar:
        await state.clear()
        await message.answer(
            text="Вебинар не найден. Попробуйте позже.",
            reply_markup=back_to_menu_keyboard(),
        )
        return

    # Экспорт в Google Sheets
    await append_registration(
        first_name=user.first_name or "",
        username=user.username or "",
        phone=phone,
        email="",
        webinar_title=webinar["title"],
        full_name=full_name,
        position=position,
    )

    await state.clear()

    # Сообщение об успешной регистрации
    text = (
        f"\u2705 Вы зарегистрированы на вебинар «{webinar['title']}»!\n\n"
        f"\U0001f4c5 Дата: {webinar['date']}\n"
        f"\u23f0 Время: {webinar['time']} (по {webinar['timezone']})\n\n"
        f"Мы напомним вам:\n"
        f"\u2022 За 1 день до начала\n"
        f"\u2022 За 1 час — с ссылкой на эфир\n\n"
        f"Ожидайте напоминания! \U0001f514"
    )

    await message.answer(
        text=text,
        reply_markup=post_registration_keyboard(),
    )


# ========================================
# О ЦЕНТРЕ
# ========================================


@router.callback_query(F.data == "about_center")
async def show_about_center(callback: CallbackQuery) -> None:
    """Показать информацию о центре."""
    await callback.answer()
    text = await get_center_info()
    await callback.message.edit_text(
        text=f"\U0001f3e2 <b>О нашем центре</b>\n\n{text}",
        reply_markup=about_center_keyboard(),
        parse_mode="HTML",
    )


# ========================================
# ПРОГРАММЫ
# ========================================


@router.callback_query(F.data == "programs")
async def show_programs(callback: CallbackQuery) -> None:
    """Показать список программ."""
    await callback.answer()
    programs = await get_all_active_programs()

    if not programs:
        await callback.message.edit_text(
            text="На данный момент программы не добавлены.\nСледите за обновлениями!",
            reply_markup=back_to_menu_keyboard(),
        )
        return

    text = "\U0001f393 <b>Наши программы</b>\n\nВыберите программу для подробной информации:"
    await callback.message.edit_text(
        text=text,
        reply_markup=programs_list_keyboard(programs),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("program_detail_"))
async def show_program_detail(callback: CallbackQuery) -> None:
    """Показать детали программы."""
    await callback.answer()
    program_id = int(callback.data.split("_")[-1])
    program = await get_program_by_id(program_id)

    if not program:
        await callback.message.edit_text(
            text="Программа не найдена.",
            reply_markup=back_to_menu_keyboard(),
        )
        return

    lines = [f"\U0001f4d6 <b>{program['name']}</b>\n"]
    if program.get("target_audience"):
        lines.append(f"\U0001f465 <b>Для кого:</b> {program['target_audience']}")
    if program.get("result"):
        lines.append(f"\U0001f3af <b>Результат:</b> {program['result']}")
    if program.get("duration"):
        lines.append(f"\u23f0 <b>Длительность:</b> {program['duration']}")
    if program.get("format"):
        lines.append(f"\U0001f4bb <b>Формат:</b> {program['format']}")

    text = "\n".join(lines)

    await callback.message.edit_text(
        text=text,
        reply_markup=program_detail_keyboard(program_id),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("enroll_program_"))
async def enroll_program(callback: CallbackQuery, state: FSMContext) -> None:
    """Обработка кнопки 'Записаться' на программу — запуск сбора контактов."""
    await callback.answer()
    program_id = int(callback.data.split("_")[-1])
    program = await get_program_by_id(program_id)
    program_name = program["name"] if program else "программу"

    # Переадресуем на сбор контактов через callback
    from bot.handlers.contact import start_contact_collection
    await start_contact_collection(
        callback,
        state,
        source=f"Запись на программу: {program_name}",
    )


# ========================================
# МАТЕРИАЛЫ И МЕНЕДЖЕР
# ========================================


@router.callback_query(F.data == "request_materials")
async def request_materials(callback: CallbackQuery, state: FSMContext) -> None:
    """Запрос подборки материалов — отправка файла/ссылки или сбор контактов."""
    await callback.answer()

    materials_file_id = await get_setting("materials_file_id")
    materials_link = await get_setting("materials_link")
    materials_text = await get_setting("materials_text") or "Вот подборка полезных материалов по теме обучения:"

    if materials_file_id:
        # Отправляем файл с текстом
        await callback.message.answer_document(
            document=materials_file_id,
            caption=materials_text,
        )
        await callback.message.answer(
            text="Если у вас остались вопросы — свяжитесь с менеджером.",
            reply_markup=back_to_menu_keyboard(),
        )
        return

    if materials_link:
        # Отправляем текст со ссылкой
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="\U0001f4ce Открыть материалы", url=materials_link)],
                [InlineKeyboardButton(text="\u2b05\ufe0f Главное меню", callback_data="back_to_menu")],
            ]
        )
        await callback.message.edit_text(
            text=materials_text,
            reply_markup=keyboard,
        )
        return

    # Ничего не настроено — собираем контакт
    await callback.message.edit_text(
        text="\U0001f4da Подборка материалов пока готовится.\n\n"
             "Оставьте свои контакты, и мы отправим её вам, как только она будет готова!",
    )
    from bot.handlers.contact import start_contact_collection
    await start_contact_collection(
        callback,
        state,
        source="Запрос подборки материалов",
    )


@router.callback_query(F.data == "contact_manager")
async def contact_manager(callback: CallbackQuery, state: FSMContext) -> None:
    """Связаться с менеджером — показать контакт или запуск сбора контактов."""
    await callback.answer()

    manager_contact = await get_setting("manager_contact")

    if manager_contact:
        # Формируем ссылку на менеджера
        if manager_contact.startswith("@"):
            username = manager_contact.lstrip("@")
            manager_url = f"https://t.me/{username}"
            display_name = manager_contact
        elif manager_contact.startswith("http"):
            manager_url = manager_contact
            display_name = manager_contact
        else:
            # Предполагаем username без @
            manager_url = f"https://t.me/{manager_contact}"
            display_name = f"@{manager_contact}"

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="\U0001f4ac Написать менеджеру", url=manager_url)],
                [InlineKeyboardButton(text="\u2b05\ufe0f Главное меню", callback_data="back_to_menu")],
            ]
        )
        await callback.message.edit_text(
            text=f"\U0001f464 Напишите нашему менеджеру: {display_name}\n\n"
                 f"Он ответит вам в ближайшее время!",
            reply_markup=keyboard,
        )
        return

    # Менеджер не задан — собираем контакты как раньше
    from bot.handlers.contact import start_contact_collection
    await start_contact_collection(
        callback,
        state,
        source="Связаться с менеджером",
    )
