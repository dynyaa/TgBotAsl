"""
FSM-состояния для форм сбора данных.
"""

from aiogram.fsm.state import State, StatesGroup


class ContactForm(StatesGroup):
    """Форма сбора контактных данных пользователя."""
    waiting_for_phone = State()
    waiting_for_email = State()


class WebinarRegistrationForm(StatesGroup):
    """Форма регистрации на вебинар (ФИО, телефон, должность)."""
    waiting_for_full_name = State()
    waiting_for_phone = State()
    waiting_for_position = State()


class AdminWebinarForm(StatesGroup):
    """Форма создания/редактирования вебинара (админ)."""
    waiting_for_title = State()
    waiting_for_date = State()
    waiting_for_time = State()
    waiting_for_timezone = State()
    waiting_for_link = State()


class AdminEditWebinarForm(StatesGroup):
    """Форма редактирования вебинара (админ) — выбор поля."""
    waiting_for_field = State()
    waiting_for_value = State()


class AdminProgramForm(StatesGroup):
    """Форма создания программы (админ)."""
    waiting_for_name = State()
    waiting_for_target = State()
    waiting_for_result = State()
    waiting_for_duration = State()
    waiting_for_format = State()


class AdminEditProgramForm(StatesGroup):
    """Форма редактирования программы (админ) — выбор поля."""
    waiting_for_field = State()
    waiting_for_value = State()


class AdminCenterInfoForm(StatesGroup):
    """Форма редактирования информации о центре (админ)."""
    waiting_for_text = State()


class AdminSettingsForm(StatesGroup):
    """Форма редактирования настроек бота (админ)."""
    waiting_for_manager_contact = State()
    waiting_for_channel_link = State()
    waiting_for_materials = State()       # принимает и файл (document), и текст-ссылку
    waiting_for_materials_text = State()
