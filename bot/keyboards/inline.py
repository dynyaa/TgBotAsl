"""
Inline-клавиатуры для всех экранов бота.
"""

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)

from bot.config import CHANNEL_LINK


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню после /start."""
    buttons = [
        [InlineKeyboardButton(text="\U0001f4c5 Вебинары", callback_data="webinars")],
        [InlineKeyboardButton(text="\U0001f4cc О центре", callback_data="about_center")],
        [InlineKeyboardButton(text="\U0001f393 Программы", callback_data="programs")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def webinars_list_keyboard(webinars: list[dict]) -> InlineKeyboardMarkup:
    """Список активных вебинаров для пользователя."""
    buttons = []
    for w in webinars:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"\U0001f4c5 {w['title']} ({w['date']})",
                    callback_data=f"webinar_detail_{w['id']}",
                )
            ]
        )
    buttons.append(
        [InlineKeyboardButton(text="\u2b05\ufe0f Главное меню", callback_data="back_to_menu")]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def webinar_detail_keyboard(webinar_id: int) -> InlineKeyboardMarkup:
    """Кнопки на экране деталей вебинара (для пользователя)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="\u270d\ufe0f Записаться",
                    callback_data=f"register_webinar_{webinar_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="\u2b05\ufe0f К вебинарам", callback_data="webinars"
                )
            ],
        ]
    )


def post_registration_keyboard() -> InlineKeyboardMarkup:
    """Кнопки после успешной регистрации на вебинар."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="\U0001f4cc О центре", callback_data="about_center")],
            [InlineKeyboardButton(text="\U0001f393 Программы", callback_data="programs")],
            [InlineKeyboardButton(text="\u2b05\ufe0f Главное меню", callback_data="back_to_menu")],
        ]
    )


def about_center_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура на экране 'О центре'."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="\U0001f393 Посмотреть программы", callback_data="programs"
                )
            ],
            [
                InlineKeyboardButton(
                    text="\u2753 Задать вопрос", callback_data="contact_manager"
                )
            ],
            [InlineKeyboardButton(text="\u2b05\ufe0f Назад", callback_data="back_to_menu")],
        ]
    )


def programs_list_keyboard(programs: list[dict]) -> InlineKeyboardMarkup:
    """Список программ с кнопками 'Подробнее'."""
    buttons = []
    for program in programs:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"\U0001f4d6 {program['name']}",
                    callback_data=f"program_detail_{program['id']}",
                )
            ]
        )
    buttons.append(
        [InlineKeyboardButton(text="\u2b05\ufe0f Назад", callback_data="back_to_menu")]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def program_detail_keyboard(program_id: int) -> InlineKeyboardMarkup:
    """Клавиатура на экране деталей программы."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="\u270d\ufe0f Записаться",
                    callback_data=f"enroll_program_{program_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="\u2753 Оставить вопрос",
                    callback_data="contact_manager",
                )
            ],
            [
                InlineKeyboardButton(
                    text="\u2b05\ufe0f К программам", callback_data="programs"
                )
            ],
        ]
    )


def channel_invite_keyboard(channel_link: str = "") -> InlineKeyboardMarkup:
    """Клавиатура с приглашением в канал."""
    link = channel_link or CHANNEL_LINK
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="\u27a1\ufe0f Перейти в канал",
                    url=link,
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


def phone_request_keyboard() -> ReplyKeyboardMarkup:
    """Reply-клавиатура с кнопкой 'Поделиться контактом'."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="\U0001f4f1 Поделиться контактом", request_contact=True)],
            [KeyboardButton(text="\u274c Отмена")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def skip_email_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура с кнопкой 'Пропустить' для email."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="\u23e9 Пропустить", callback_data="skip_email")]
        ]
    )


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    """Кнопка возврата в главное меню."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="\u2b05\ufe0f Главное меню", callback_data="back_to_menu")]
        ]
    )


# === Админские клавиатуры ===


def admin_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню администратора."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="\U0001f4e2 Вебинары", callback_data="admin_webinars"
                )
            ],
            [
                InlineKeyboardButton(
                    text="\U0001f393 Программы", callback_data="admin_programs"
                )
            ],
            [
                InlineKeyboardButton(
                    text="\U0001f3e2 Текст 'О центре'",
                    callback_data="admin_center_info",
                )
            ],
            [
                InlineKeyboardButton(
                    text="\u2699\ufe0f Настройки",
                    callback_data="admin_settings",
                )
            ],
        ]
    )


def admin_webinars_keyboard(webinars: list[dict]) -> InlineKeyboardMarkup:
    """Список вебинаров в админке."""
    buttons = []
    for w in webinars:
        status = "\u2705" if w["is_active"] else "\u274c"
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"{status} {w['title']} ({w['date']})",
                    callback_data=f"admin_webinar_{w['id']}",
                )
            ]
        )
    buttons.append(
        [InlineKeyboardButton(text="\u2795 Добавить вебинар", callback_data="admin_add_webinar")]
    )
    buttons.append(
        [InlineKeyboardButton(text="\u2b05\ufe0f Назад", callback_data="admin_menu")]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_webinar_detail_keyboard(webinar_id: int) -> InlineKeyboardMarkup:
    """Детали вебинара в админке."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="\u270f\ufe0f Редактировать",
                    callback_data=f"admin_edit_webinar_{webinar_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="\U0001f4cb Зарегистрированные",
                    callback_data=f"admin_webinar_regs_{webinar_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="\U0001f5d1\ufe0f Удалить",
                    callback_data=f"admin_delete_webinar_{webinar_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="\u2b05\ufe0f К вебинарам", callback_data="admin_webinars"
                )
            ],
        ]
    )


def admin_edit_webinar_fields_keyboard(webinar_id: int) -> InlineKeyboardMarkup:
    """Выбор поля для редактирования вебинара."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Название",
                    callback_data=f"admin_wf_title_{webinar_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Дата",
                    callback_data=f"admin_wf_date_{webinar_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Время",
                    callback_data=f"admin_wf_time_{webinar_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Часовой пояс",
                    callback_data=f"admin_wf_timezone_{webinar_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Ссылка",
                    callback_data=f"admin_wf_link_{webinar_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Вкл/Выкл активность",
                    callback_data=f"admin_wf_toggle_{webinar_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="\u2b05\ufe0f Назад",
                    callback_data=f"admin_webinar_{webinar_id}",
                )
            ],
        ]
    )


def admin_programs_keyboard(programs: list[dict]) -> InlineKeyboardMarkup:
    """Список программ в админке."""
    buttons = []
    for p in programs:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=f"\U0001f4d6 {p['name']}",
                    callback_data=f"admin_program_{p['id']}",
                )
            ]
        )
    buttons.append(
        [
            InlineKeyboardButton(
                text="\u2795 Добавить программу", callback_data="admin_add_program"
            )
        ]
    )
    buttons.append(
        [InlineKeyboardButton(text="\u2b05\ufe0f Назад", callback_data="admin_menu")]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def admin_program_detail_keyboard(program_id: int) -> InlineKeyboardMarkup:
    """Детали программы в админке."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="\u270f\ufe0f Редактировать",
                    callback_data=f"admin_edit_program_{program_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="\U0001f5d1\ufe0f Удалить",
                    callback_data=f"admin_delete_program_{program_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="\u2b05\ufe0f К программам", callback_data="admin_programs"
                )
            ],
        ]
    )


def admin_edit_program_fields_keyboard(program_id: int) -> InlineKeyboardMarkup:
    """Выбор поля для редактирования программы."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Название",
                    callback_data=f"admin_pf_name_{program_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Для кого",
                    callback_data=f"admin_pf_target_{program_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Результат",
                    callback_data=f"admin_pf_result_{program_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Длительность",
                    callback_data=f"admin_pf_duration_{program_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="Формат",
                    callback_data=f"admin_pf_format_{program_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="\u2b05\ufe0f Назад",
                    callback_data=f"admin_program_{program_id}",
                )
            ],
        ]
    )


def admin_confirm_delete_keyboard(entity: str, entity_id: int) -> InlineKeyboardMarkup:
    """Подтверждение удаления."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="\u2705 Да, удалить",
                    callback_data=f"admin_confirm_del_{entity}_{entity_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="\u274c Отмена",
                    callback_data=f"admin_{entity}s",
                )
            ],
        ]
    )


def admin_settings_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура раздела настроек в админке."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="\U0001f464 Контакт менеджера",
                    callback_data="admin_set_manager_contact",
                )
            ],
            [
                InlineKeyboardButton(
                    text="\U0001f4e2 Ссылка на канал",
                    callback_data="admin_set_channel_link",
                )
            ],
            [
                InlineKeyboardButton(
                    text="\U0001f4ce Подборка материалов",
                    callback_data="admin_set_materials",
                )
            ],
            [
                InlineKeyboardButton(
                    text="\u270f\ufe0f Текст к подборке",
                    callback_data="admin_set_materials_text",
                )
            ],
            [
                InlineKeyboardButton(
                    text="\u2b05\ufe0f Назад",
                    callback_data="admin_menu",
                )
            ],
        ]
    )
