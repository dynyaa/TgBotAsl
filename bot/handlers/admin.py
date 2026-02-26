"""
Админ-хендлеры: управление вебинарами, программами, текстом о центре.
Доступны только для пользователя с ADMIN_ID из .env.
"""

import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.config import ADMIN_ID
from bot.states.forms import (
    AdminWebinarForm,
    AdminEditWebinarForm,
    AdminProgramForm,
    AdminEditProgramForm,
    AdminCenterInfoForm,
    AdminSettingsForm,
)
from bot.keyboards.inline import (
    admin_menu_keyboard,
    admin_webinars_keyboard,
    admin_webinar_detail_keyboard,
    admin_edit_webinar_fields_keyboard,
    admin_programs_keyboard,
    admin_program_detail_keyboard,
    admin_edit_program_fields_keyboard,
    admin_confirm_delete_keyboard,
    admin_settings_keyboard,
    back_to_menu_keyboard,
)
from bot.services.database import (
    get_all_active_webinars,
    get_webinar_by_id,
    create_webinar,
    update_webinar,
    delete_webinar,
    get_registrations_for_webinar,
    get_all_active_programs,
    get_program_by_id,
    create_program,
    update_program,
    delete_program,
    get_center_info,
    update_center_info,
    get_setting,
    set_setting,
    get_all_settings,
)

logger = logging.getLogger(__name__)

router = Router()


def is_admin(user_id: int) -> bool:
    """Проверить, является ли пользователь администратором."""
    return ADMIN_ID is not None and user_id == ADMIN_ID


# === Главное меню админа ===


@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext) -> None:
    """Команда /admin — показать меню администратора."""
    await state.clear()
    if not is_admin(message.from_user.id):
        await message.answer("У вас нет доступа к панели администратора.")
        return

    await message.answer(
        text="\U0001f6e0\ufe0f <b>Панель администратора</b>\n\nВыберите раздел:",
        reply_markup=admin_menu_keyboard(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "admin_menu")
async def admin_menu(callback: CallbackQuery, state: FSMContext) -> None:
    """Возврат в меню администратора."""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.answer()
    await state.clear()
    await callback.message.edit_text(
        text="\U0001f6e0\ufe0f <b>Панель администратора</b>\n\nВыберите раздел:",
        reply_markup=admin_menu_keyboard(),
        parse_mode="HTML",
    )


# ========================================
# ВЕБИНАРЫ
# ========================================


@router.callback_query(F.data == "admin_webinars")
async def admin_webinars_list(callback: CallbackQuery, state: FSMContext) -> None:
    """Список вебинаров."""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.answer()
    await state.clear()

    # Получаем все вебинары (включая неактивные для админа)
    import aiosqlite
    from bot.config import DB_PATH

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM webinars ORDER BY date DESC")
        rows = await cursor.fetchall()
        webinars = [dict(row) for row in rows]

    await callback.message.edit_text(
        text="\U0001f4e2 <b>Управление вебинарами</b>",
        reply_markup=admin_webinars_keyboard(webinars),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("admin_webinar_") & ~F.data.startswith("admin_webinar_regs_"))
async def admin_webinar_detail(callback: CallbackQuery) -> None:
    """Детали вебинара в админке."""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.answer()

    webinar_id = int(callback.data.split("_")[-1])
    webinar = await get_webinar_by_id(webinar_id)

    if not webinar:
        await callback.message.edit_text(
            "Вебинар не найден.", reply_markup=back_to_menu_keyboard()
        )
        return

    status = "\u2705 Активен" if webinar["is_active"] else "\u274c Неактивен"
    text = (
        f"\U0001f4e2 <b>{webinar['title']}</b>\n\n"
        f"\U0001f4c5 Дата: {webinar['date']}\n"
        f"\u23f0 Время: {webinar['time']}\n"
        f"\U0001f30d Часовой пояс: {webinar['timezone']}\n"
        f"\U0001f517 Ссылка: {webinar['link'] or 'не указана'}\n"
        f"Статус: {status}"
    )

    await callback.message.edit_text(
        text=text,
        reply_markup=admin_webinar_detail_keyboard(webinar_id),
        parse_mode="HTML",
    )


# --- Создание вебинара ---


@router.callback_query(F.data == "admin_add_webinar")
async def admin_add_webinar_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Начать создание вебинара."""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.answer()
    await state.set_state(AdminWebinarForm.waiting_for_title)
    await callback.message.edit_text("Введите название вебинара:")


@router.message(AdminWebinarForm.waiting_for_title, F.text)
async def admin_webinar_title(message: Message, state: FSMContext) -> None:
    """Получить название вебинара."""
    if not is_admin(message.from_user.id):
        return
    await state.update_data(title=message.text.strip())
    await state.set_state(AdminWebinarForm.waiting_for_date)
    await message.answer("Введите дату вебинара (формат: ДД.ММ.ГГГГ):")


@router.message(AdminWebinarForm.waiting_for_date, F.text)
async def admin_webinar_date(message: Message, state: FSMContext) -> None:
    """Получить дату вебинара."""
    if not is_admin(message.from_user.id):
        return
    await state.update_data(date=message.text.strip())
    await state.set_state(AdminWebinarForm.waiting_for_time)
    await message.answer("Введите время вебинара (формат: ЧЧ:ММ):")


@router.message(AdminWebinarForm.waiting_for_time, F.text)
async def admin_webinar_time(message: Message, state: FSMContext) -> None:
    """Получить время вебинара."""
    if not is_admin(message.from_user.id):
        return
    await state.update_data(time=message.text.strip())
    await state.set_state(AdminWebinarForm.waiting_for_timezone)
    await message.answer("Введите часовой пояс (например: Астана, Москва):")


@router.message(AdminWebinarForm.waiting_for_timezone, F.text)
async def admin_webinar_timezone(message: Message, state: FSMContext) -> None:
    """Получить часовой пояс."""
    if not is_admin(message.from_user.id):
        return
    await state.update_data(timezone=message.text.strip())
    await state.set_state(AdminWebinarForm.waiting_for_link)
    await message.answer(
        "Введите ссылку на вебинар (или отправьте '-' чтобы добавить позже):"
    )


@router.message(AdminWebinarForm.waiting_for_link, F.text)
async def admin_webinar_link(message: Message, state: FSMContext) -> None:
    """Получить ссылку и создать вебинар."""
    if not is_admin(message.from_user.id):
        return

    link = message.text.strip()
    if link == "-":
        link = ""

    data = await state.get_data()
    webinar_id = await create_webinar(
        title=data["title"],
        date=data["date"],
        time=data["time"],
        timezone=data.get("timezone", "Астана"),
        link=link,
    )

    await state.clear()

    # Планируем напоминания для нового вебинара
    from bot.services.scheduler import schedule_webinar_reminders

    webinar = await get_webinar_by_id(webinar_id)
    if webinar:
        await schedule_webinar_reminders(message.bot, webinar)

    await message.answer(
        text=(
            f"\u2705 Вебинар создан!\n\n"
            f"<b>{data['title']}</b>\n"
            f"\U0001f4c5 {data['date']} в {data['time']} (по {data.get('timezone', 'Астана')})\n"
            f"\U0001f517 {link or 'ссылка не указана'}"
        ),
        reply_markup=admin_menu_keyboard(),
        parse_mode="HTML",
    )


# --- Редактирование вебинара ---


@router.callback_query(F.data.startswith("admin_edit_webinar_"))
async def admin_edit_webinar_menu(callback: CallbackQuery, state: FSMContext) -> None:
    """Меню выбора поля для редактирования вебинара."""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.answer()

    webinar_id = int(callback.data.split("_")[-1])
    await state.clear()

    await callback.message.edit_text(
        text="Выберите поле для редактирования:",
        reply_markup=admin_edit_webinar_fields_keyboard(webinar_id),
    )


@router.callback_query(F.data.startswith("admin_wf_"))
async def admin_webinar_field_select(callback: CallbackQuery, state: FSMContext) -> None:
    """Выбор конкретного поля вебинара для редактирования."""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.answer()

    parts = callback.data.split("_")
    field = parts[2]  # admin_wf_<field>_<id>
    webinar_id = int(parts[3])

    # Переключение активности — без FSM
    if field == "toggle":
        webinar = await get_webinar_by_id(webinar_id)
        if webinar:
            new_status = 0 if webinar["is_active"] else 1
            await update_webinar(webinar_id, is_active=new_status)
            status_text = "активирован" if new_status else "деактивирован"
            await callback.message.edit_text(
                text=f"\u2705 Вебинар {status_text}.",
                reply_markup=admin_webinar_detail_keyboard(webinar_id),
            )
        return

    field_map = {
        "title": ("название", "title"),
        "date": ("дату (ДД.ММ.ГГГГ)", "date"),
        "time": ("время (ЧЧ:ММ)", "time"),
        "timezone": ("часовой пояс", "timezone"),
        "link": ("ссылку", "link"),
    }

    display_name, db_field = field_map.get(field, ("значение", field))
    await state.set_state(AdminEditWebinarForm.waiting_for_value)
    await state.update_data(webinar_id=webinar_id, field=db_field)

    await callback.message.edit_text(f"Введите новое {display_name}:")


@router.message(AdminEditWebinarForm.waiting_for_value, F.text)
async def admin_webinar_edit_value(message: Message, state: FSMContext) -> None:
    """Применить новое значение поля вебинара."""
    if not is_admin(message.from_user.id):
        return

    data = await state.get_data()
    webinar_id = data["webinar_id"]
    field = data["field"]

    await update_webinar(webinar_id, **{field: message.text.strip()})
    await state.clear()

    # Перепланировать напоминания, если изменились дата/время
    if field in ("date", "time", "timezone"):
        from bot.services.scheduler import schedule_webinar_reminders

        webinar = await get_webinar_by_id(webinar_id)
        if webinar:
            await schedule_webinar_reminders(message.bot, webinar)

    await message.answer(
        text="\u2705 Вебинар обновлён!",
        reply_markup=admin_webinar_detail_keyboard(webinar_id),
    )


# --- Удаление вебинара ---


@router.callback_query(F.data.startswith("admin_delete_webinar_"))
async def admin_delete_webinar_confirm(callback: CallbackQuery) -> None:
    """Подтверждение удаления вебинара."""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.answer()

    webinar_id = int(callback.data.split("_")[-1])
    webinar = await get_webinar_by_id(webinar_id)
    title = webinar["title"] if webinar else "вебинар"

    await callback.message.edit_text(
        text=f"Вы уверены, что хотите удалить вебинар «{title}»?",
        reply_markup=admin_confirm_delete_keyboard("webinar", webinar_id),
    )


@router.callback_query(F.data.startswith("admin_confirm_del_webinar_"))
async def admin_delete_webinar_execute(callback: CallbackQuery) -> None:
    """Выполнение удаления вебинара."""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.answer()

    webinar_id = int(callback.data.split("_")[-1])
    await delete_webinar(webinar_id)

    await callback.message.edit_text(
        text="\u2705 Вебинар удалён.",
        reply_markup=admin_menu_keyboard(),
    )


# --- Зарегистрированные на вебинар ---


@router.callback_query(F.data.startswith("admin_webinar_regs_"))
async def admin_webinar_registrations(callback: CallbackQuery) -> None:
    """Показать список зарегистрированных на вебинар."""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.answer()

    webinar_id = int(callback.data.split("_")[-1])
    webinar = await get_webinar_by_id(webinar_id)
    registrations = await get_registrations_for_webinar(webinar_id)

    if not registrations:
        await callback.message.edit_text(
            text=f"На вебинар «{webinar['title'] if webinar else ''}» пока нет регистраций.",
            reply_markup=admin_webinar_detail_keyboard(webinar_id),
        )
        return

    lines = [
        f"\U0001f4cb <b>Зарегистрированные на «{webinar['title']}»</b>\n",
        f"Всего: {len(registrations)}\n",
    ]
    for i, reg in enumerate(registrations, 1):
        full_name = reg.get("full_name") or reg.get("first_name", "—")
        username = f"@{reg['username']}" if reg.get("username") else "нет username"
        phone = reg.get("phone") or "нет телефона"
        position = reg.get("position") or "не указана"
        lines.append(
            f"{i}. {full_name} ({username})\n"
            f"   Тел: {phone} | Должность: {position}"
        )

    text = "\n".join(lines)
    # Обрезаем если слишком длинный текст
    if len(text) > 4000:
        text = text[:4000] + "\n\n... (список обрезан)"

    await callback.message.edit_text(
        text=text,
        reply_markup=admin_webinar_detail_keyboard(webinar_id),
        parse_mode="HTML",
    )


# ========================================
# ПРОГРАММЫ
# ========================================


@router.callback_query(F.data == "admin_programs")
async def admin_programs_list(callback: CallbackQuery, state: FSMContext) -> None:
    """Список программ в админке."""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.answer()
    await state.clear()

    # Получаем все программы (включая неактивные для админа)
    import aiosqlite
    from bot.config import DB_PATH

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM programs ORDER BY id")
        rows = await cursor.fetchall()
        programs = [dict(row) for row in rows]

    await callback.message.edit_text(
        text="\U0001f393 <b>Управление программами</b>",
        reply_markup=admin_programs_keyboard(programs),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("admin_program_") & ~F.data.startswith("admin_program_detail"))
async def admin_program_detail(callback: CallbackQuery) -> None:
    """Детали программы в админке."""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.answer()

    program_id = int(callback.data.split("_")[-1])
    program = await get_program_by_id(program_id)

    if not program:
        await callback.message.edit_text(
            "Программа не найдена.", reply_markup=admin_menu_keyboard()
        )
        return

    lines = [f"\U0001f4d6 <b>{program['name']}</b>\n"]
    if program.get("target_audience"):
        lines.append(f"\U0001f465 Для кого: {program['target_audience']}")
    if program.get("result"):
        lines.append(f"\U0001f3af Результат: {program['result']}")
    if program.get("duration"):
        lines.append(f"\u23f0 Длительность: {program['duration']}")
    if program.get("format"):
        lines.append(f"\U0001f4bb Формат: {program['format']}")

    text = "\n".join(lines)

    await callback.message.edit_text(
        text=text,
        reply_markup=admin_program_detail_keyboard(program_id),
        parse_mode="HTML",
    )


# --- Создание программы ---


@router.callback_query(F.data == "admin_add_program")
async def admin_add_program_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Начать создание программы."""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.answer()
    await state.set_state(AdminProgramForm.waiting_for_name)
    await callback.message.edit_text("Введите название программы:")


@router.message(AdminProgramForm.waiting_for_name, F.text)
async def admin_program_name(message: Message, state: FSMContext) -> None:
    """Получить название программы."""
    if not is_admin(message.from_user.id):
        return
    await state.update_data(name=message.text.strip())
    await state.set_state(AdminProgramForm.waiting_for_target)
    await message.answer("Для кого эта программа? (целевая аудитория):")


@router.message(AdminProgramForm.waiting_for_target, F.text)
async def admin_program_target(message: Message, state: FSMContext) -> None:
    """Получить целевую аудиторию."""
    if not is_admin(message.from_user.id):
        return
    await state.update_data(target_audience=message.text.strip())
    await state.set_state(AdminProgramForm.waiting_for_result)
    await message.answer("Какой результат получит участник?")


@router.message(AdminProgramForm.waiting_for_result, F.text)
async def admin_program_result(message: Message, state: FSMContext) -> None:
    """Получить результат программы."""
    if not is_admin(message.from_user.id):
        return
    await state.update_data(result=message.text.strip())
    await state.set_state(AdminProgramForm.waiting_for_duration)
    await message.answer("Длительность программы (например: 2 месяца, 40 часов):")


@router.message(AdminProgramForm.waiting_for_duration, F.text)
async def admin_program_duration(message: Message, state: FSMContext) -> None:
    """Получить длительность."""
    if not is_admin(message.from_user.id):
        return
    await state.update_data(duration=message.text.strip())
    await state.set_state(AdminProgramForm.waiting_for_format)
    await message.answer("Формат обучения (например: онлайн, очно, смешанный):")


@router.message(AdminProgramForm.waiting_for_format, F.text)
async def admin_program_format(message: Message, state: FSMContext) -> None:
    """Получить формат и создать программу."""
    if not is_admin(message.from_user.id):
        return

    data = await state.get_data()
    await create_program(
        name=data["name"],
        target_audience=data.get("target_audience", ""),
        result=data.get("result", ""),
        duration=data.get("duration", ""),
        fmt=message.text.strip(),
    )

    await state.clear()

    await message.answer(
        text=f"\u2705 Программа «{data['name']}» создана!",
        reply_markup=admin_menu_keyboard(),
    )


# --- Редактирование программы ---


@router.callback_query(F.data.startswith("admin_edit_program_"))
async def admin_edit_program_menu(callback: CallbackQuery, state: FSMContext) -> None:
    """Меню выбора поля для редактирования программы."""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.answer()

    program_id = int(callback.data.split("_")[-1])
    await state.clear()

    await callback.message.edit_text(
        text="Выберите поле для редактирования:",
        reply_markup=admin_edit_program_fields_keyboard(program_id),
    )


@router.callback_query(F.data.startswith("admin_pf_"))
async def admin_program_field_select(callback: CallbackQuery, state: FSMContext) -> None:
    """Выбор конкретного поля программы для редактирования."""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.answer()

    parts = callback.data.split("_")
    field = parts[2]  # admin_pf_<field>_<id>
    program_id = int(parts[3])

    field_map = {
        "name": ("название", "name"),
        "target": ("целевую аудиторию", "target_audience"),
        "result": ("результат", "result"),
        "duration": ("длительность", "duration"),
        "format": ("формат", "format"),
    }

    display_name, db_field = field_map.get(field, ("значение", field))
    await state.set_state(AdminEditProgramForm.waiting_for_value)
    await state.update_data(program_id=program_id, field=db_field)

    await callback.message.edit_text(f"Введите новое {display_name}:")


@router.message(AdminEditProgramForm.waiting_for_value, F.text)
async def admin_program_edit_value(message: Message, state: FSMContext) -> None:
    """Применить новое значение поля программы."""
    if not is_admin(message.from_user.id):
        return

    data = await state.get_data()
    program_id = data["program_id"]
    field = data["field"]

    await update_program(program_id, **{field: message.text.strip()})
    await state.clear()

    await message.answer(
        text="\u2705 Программа обновлена!",
        reply_markup=admin_program_detail_keyboard(program_id),
    )


# --- Удаление программы ---


@router.callback_query(F.data.startswith("admin_delete_program_"))
async def admin_delete_program_confirm(callback: CallbackQuery) -> None:
    """Подтверждение удаления программы."""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.answer()

    program_id = int(callback.data.split("_")[-1])
    program = await get_program_by_id(program_id)
    name = program["name"] if program else "программу"

    await callback.message.edit_text(
        text=f"Вы уверены, что хотите удалить программу «{name}»?",
        reply_markup=admin_confirm_delete_keyboard("program", program_id),
    )


@router.callback_query(F.data.startswith("admin_confirm_del_program_"))
async def admin_delete_program_execute(callback: CallbackQuery) -> None:
    """Выполнение удаления программы."""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.answer()

    program_id = int(callback.data.split("_")[-1])
    await delete_program(program_id)

    await callback.message.edit_text(
        text="\u2705 Программа удалена.",
        reply_markup=admin_menu_keyboard(),
    )


# ========================================
# ИНФОРМАЦИЯ О ЦЕНТРЕ
# ========================================


@router.callback_query(F.data == "admin_center_info")
async def admin_center_info_show(callback: CallbackQuery, state: FSMContext) -> None:
    """Показать текущий текст о центре и предложить редактирование."""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.answer()
    await state.clear()

    text = await get_center_info()

    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="\u270f\ufe0f Изменить текст",
                    callback_data="admin_edit_center_info",
                )
            ],
            [
                InlineKeyboardButton(
                    text="\u2b05\ufe0f Назад", callback_data="admin_menu"
                )
            ],
        ]
    )

    await callback.message.edit_text(
        text=f"\U0001f3e2 <b>Текущий текст 'О центре':</b>\n\n{text}",
        reply_markup=keyboard,
        parse_mode="HTML",
    )


@router.callback_query(F.data == "admin_edit_center_info")
async def admin_edit_center_info_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Начать редактирование текста о центре."""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.answer()
    await state.set_state(AdminCenterInfoForm.waiting_for_text)

    await callback.message.edit_text(
        "Отправьте новый текст для раздела 'О центре':"
    )


@router.message(AdminCenterInfoForm.waiting_for_text, F.text)
async def admin_center_info_save(message: Message, state: FSMContext) -> None:
    """Сохранить новый текст о центре."""
    if not is_admin(message.from_user.id):
        return

    await update_center_info(message.text.strip())
    await state.clear()

    await message.answer(
        text="\u2705 Текст 'О центре' обновлён!",
        reply_markup=admin_menu_keyboard(),
    )


# ========================================
# НАСТРОЙКИ
# ========================================


@router.callback_query(F.data == "admin_settings")
async def admin_settings_show(callback: CallbackQuery, state: FSMContext) -> None:
    """Показать раздел настроек с текущими значениями."""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.answer()
    await state.clear()

    settings = await get_all_settings()

    manager = settings.get("manager_contact", "") or "не задан"
    channel = settings.get("channel_link", "") or "не задана"
    materials_file = settings.get("materials_file_id", "")
    materials_link = settings.get("materials_link", "")
    materials_text = settings.get("materials_text", "") or "не задан"

    if materials_file:
        materials_status = "загружен файл"
    elif materials_link:
        materials_status = f"ссылка: {materials_link}"
    else:
        materials_status = "не задана"

    text = (
        "\u2699\ufe0f <b>Настройки бота</b>\n\n"
        f"\U0001f464 <b>Контакт менеджера:</b> {manager}\n"
        f"\U0001f4e2 <b>Ссылка на канал:</b> {channel}\n"
        f"\U0001f4ce <b>Подборка материалов:</b> {materials_status}\n"
        f"\u270f\ufe0f <b>Текст к подборке:</b> {materials_text}\n\n"
        "Выберите настройку для изменения:"
    )

    await callback.message.edit_text(
        text=text,
        reply_markup=admin_settings_keyboard(),
        parse_mode="HTML",
    )


# --- Контакт менеджера ---


@router.callback_query(F.data == "admin_set_manager_contact")
async def admin_set_manager_contact_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Начать ввод контакта менеджера."""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.answer()

    current = await get_setting("manager_contact")
    current_text = f"Текущее значение: {current}" if current else "Сейчас не задан"

    await state.set_state(AdminSettingsForm.waiting_for_manager_contact)
    await callback.message.edit_text(
        f"\U0001f464 <b>Контакт менеджера</b>\n\n"
        f"{current_text}\n\n"
        f"Введите @username менеджера или ссылку на Telegram-профиль\n"
        f"(например: @manager или https://t.me/manager).\n\n"
        f"Для очистки отправьте '-'",
        parse_mode="HTML",
    )


@router.message(AdminSettingsForm.waiting_for_manager_contact, F.text)
async def admin_set_manager_contact_save(message: Message, state: FSMContext) -> None:
    """Сохранить контакт менеджера."""
    if not is_admin(message.from_user.id):
        return

    value = message.text.strip()
    if value == "-":
        value = ""

    await set_setting("manager_contact", value)
    await state.clear()

    display = value if value else "очищен"
    await message.answer(
        text=f"\u2705 Контакт менеджера обновлён: {display}",
        reply_markup=admin_settings_keyboard(),
    )


# --- Ссылка на канал ---


@router.callback_query(F.data == "admin_set_channel_link")
async def admin_set_channel_link_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Начать ввод ссылки на канал."""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.answer()

    current = await get_setting("channel_link")
    current_text = f"Текущее значение: {current}" if current else "Сейчас не задана"

    await state.set_state(AdminSettingsForm.waiting_for_channel_link)
    await callback.message.edit_text(
        f"\U0001f4e2 <b>Ссылка на канал</b>\n\n"
        f"{current_text}\n\n"
        f"Введите новую ссылку на Telegram-канал\n"
        f"(например: https://t.me/yourchannel):",
        parse_mode="HTML",
    )


@router.message(AdminSettingsForm.waiting_for_channel_link, F.text)
async def admin_set_channel_link_save(message: Message, state: FSMContext) -> None:
    """Сохранить ссылку на канал."""
    if not is_admin(message.from_user.id):
        return

    value = message.text.strip()
    await set_setting("channel_link", value)
    await state.clear()

    await message.answer(
        text=f"\u2705 Ссылка на канал обновлена: {value}",
        reply_markup=admin_settings_keyboard(),
    )


# --- Подборка материалов (файл или ссылка) ---


@router.callback_query(F.data == "admin_set_materials")
async def admin_set_materials_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Начать загрузку материалов."""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.answer()

    materials_file = await get_setting("materials_file_id")
    materials_link = await get_setting("materials_link")

    if materials_file:
        current_text = "Сейчас загружен файл"
    elif materials_link:
        current_text = f"Сейчас ссылка: {materials_link}"
    else:
        current_text = "Сейчас не задана"

    await state.set_state(AdminSettingsForm.waiting_for_materials)
    await callback.message.edit_text(
        f"\U0001f4ce <b>Подборка материалов</b>\n\n"
        f"{current_text}\n\n"
        f"Отправьте файл (PDF, DOC и т.д.) — бот сохранит его для отправки пользователям.\n"
        f"Или отправьте ссылку текстом.\n\n"
        f"Для очистки отправьте '-'",
        parse_mode="HTML",
    )


@router.message(AdminSettingsForm.waiting_for_materials, F.document)
async def admin_set_materials_file(message: Message, state: FSMContext) -> None:
    """Сохранить файл материалов (по file_id)."""
    if not is_admin(message.from_user.id):
        return

    file_id = message.document.file_id
    await set_setting("materials_file_id", file_id)
    await set_setting("materials_link", "")  # очищаем ссылку — приоритет у файла
    await state.clear()

    await message.answer(
        text=f"\u2705 Файл материалов сохранён!\n"
             f"Имя файла: {message.document.file_name or 'без имени'}",
        reply_markup=admin_settings_keyboard(),
    )


@router.message(AdminSettingsForm.waiting_for_materials, F.text)
async def admin_set_materials_link(message: Message, state: FSMContext) -> None:
    """Сохранить ссылку на материалы (или очистить)."""
    if not is_admin(message.from_user.id):
        return

    value = message.text.strip()
    if value == "-":
        await set_setting("materials_file_id", "")
        await set_setting("materials_link", "")
        await state.clear()
        await message.answer(
            text="\u2705 Подборка материалов очищена.",
            reply_markup=admin_settings_keyboard(),
        )
        return

    await set_setting("materials_link", value)
    await set_setting("materials_file_id", "")  # очищаем file_id — приоритет у ссылки
    await state.clear()

    await message.answer(
        text=f"\u2705 Ссылка на материалы сохранена: {value}",
        reply_markup=admin_settings_keyboard(),
    )


# --- Текст к подборке материалов ---


@router.callback_query(F.data == "admin_set_materials_text")
async def admin_set_materials_text_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Начать ввод текста к подборке материалов."""
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.answer()

    current = await get_setting("materials_text")
    current_text = f"Текущий текст:\n{current}" if current else "Сейчас не задан"

    await state.set_state(AdminSettingsForm.waiting_for_materials_text)
    await callback.message.edit_text(
        f"\u270f\ufe0f <b>Текст к подборке материалов</b>\n\n"
        f"{current_text}\n\n"
        f"Введите новый текст, который будет отправлен вместе с подборкой материалов:",
        parse_mode="HTML",
    )


@router.message(AdminSettingsForm.waiting_for_materials_text, F.text)
async def admin_set_materials_text_save(message: Message, state: FSMContext) -> None:
    """Сохранить текст к подборке материалов."""
    if not is_admin(message.from_user.id):
        return

    value = message.text.strip()
    await set_setting("materials_text", value)
    await state.clear()

    await message.answer(
        text="\u2705 Текст к подборке обновлён!",
        reply_markup=admin_settings_keyboard(),
    )
