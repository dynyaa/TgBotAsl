# Деплой Telegram-бота на Google Cloud

## Что нужно подготовить

| Параметр | Где взять |
|----------|-----------|
| **BOT_TOKEN** | @BotFather в Telegram -> `/newbot` -> скопировать токен |
| **ADMIN_ID** | @userinfobot в Telegram -> `/start` -> скопировать Id |
| **GOOGLE_SHEET_ID** | Создать таблицу на sheets.google.com, из URL скопировать часть между `/d/` и `/edit` |
| **CHANNEL_LINK** | Ссылка на ваш Telegram-канал (опционально) |

---

## 1. Google Cloud: создание VM

1. Зарегистрируйтесь на [cloud.google.com](https://cloud.google.com) (нужна карта, но списаний не будет)
2. **Compute Engine** -> **VM Instances** -> **Create Instance**

| Параметр | Значение |
|----------|----------|
| Region | `us-central1` (только US-регионы бесплатны!) |
| Machine type | `e2-micro` (free tier) |
| Boot disk | Ubuntu 22.04 LTS, 30 GB, Standard |

3. Нажмите **Create**

---

## 2. Установка бота

Нажмите **SSH** рядом с VM. В терминале выполните по порядку:

```bash
# Установка зависимостей системы
sudo apt update && sudo apt install -y python3-pip python3-venv git

# Клонирование репозитория
git clone https://github.com/dynyaa/tgbotasl.git
cd tgbotasl

# Создание .env файла
nano .env
```

Вставьте в редактор (подставьте свои значения):

```
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
CHANNEL_LINK=https://t.me/your_channel
GOOGLE_SHEET_ID=1aBc2DeF3gHi4JkL5mNo6PqR
GOOGLE_CREDENTIALS_PATH=credentials.json
ADMIN_ID=123456789
```

Сохранить: **Ctrl+O** -> **Enter** -> **Ctrl+X**

```bash
# Установка Python-окружения
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Тестовый запуск (Ctrl+C чтобы остановить)
python run.py
```

Если в Telegram бот отвечает на `/start` — все работает.

---

## 3. Автозапуск (systemd)

```bash
# Узнайте ваше имя пользователя
whoami
```

```bash
sudo nano /etc/systemd/system/tgbot.service
```

Вставьте (замените `USERNAME` на результат `whoami`):

```ini
[Unit]
Description=Telegram Bot
After=network.target

[Service]
User=USERNAME
WorkingDirectory=/home/USERNAME/tgbotasl
ExecStart=/home/USERNAME/tgbotasl/venv/bin/python run.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Сохранить: **Ctrl+O** -> **Enter** -> **Ctrl+X**

```bash
sudo systemctl enable tgbot
sudo systemctl start tgbot
sudo systemctl status tgbot
```

Если `active (running)` — бот работает 24/7. Можно закрыть SSH — бот продолжит работать.

---

## 4. Защита от списаний

1. **Billing** -> **Budgets & alerts** -> **Create budget** -> сумма: **$1** -> **Finish**
2. Проверьте **Billing** -> **Overview** — должно быть **$0.00**
3. Убедитесь что у вас **только одна VM** типа `e2-micro` в **US-регионе**

При этих условиях сервер полностью бесплатный (Always Free Tier).

---

## 5. (Опционально) Google Sheets API

Без этого бот работает, но не экспортирует заявки в таблицу.

1. [console.cloud.google.com](https://console.cloud.google.com) -> **API и сервисы** -> **Библиотека**
2. Включить **Google Sheets API** и **Google Drive API**
3. **Учетные данные** -> **Создать** -> **Сервисный аккаунт** -> назвать -> **Создать**
4. Открыть аккаунт -> **Ключи** -> **Добавить ключ** -> **JSON** -> скачается `credentials.json`
5. Из `credentials.json` скопировать `client_email`
6. В Google Таблице -> **Настройки доступа** -> вставить email -> **Редактор** -> **Отправить**
7. Загрузить файл на сервер: в SSH нажать **Upload file**, затем:
   ```bash
   mv ~/credentials.json ~/tgbotasl/credentials.json
   sudo systemctl restart tgbot
   ```

---

## 6. Управление ботом

### Через Telegram (администрирование)

Отправьте `/admin` боту:
- **Вебинары** -> **Добавить вебинар** (название, дата ДД.ММ.ГГГГ, время ЧЧ:ММ, часовой пояс, ссылка)
- **Программы** -> добавить/редактировать программы
- **Настройки** -> контакт менеджера, ссылка на канал, материалы

### Через SSH (технические команды)

```bash
sudo journalctl -u tgbot -f          # логи в реальном времени
sudo systemctl restart tgbot          # перезапуск
sudo systemctl stop tgbot             # остановка
sudo systemctl status tgbot           # статус

# Обновление кода
cd ~/tgbotasl && git pull && sudo systemctl restart tgbot

# Редактирование настроек
nano ~/tgbotasl/.env && sudo systemctl restart tgbot

# Бекап базы данных
cp ~/tgbotasl/bot_database.db ~/backup_$(date +%Y%m%d).db
```

---

## Проблемы и решения

| Проблема | Решение |
|----------|---------|
| Бот не отвечает | `sudo systemctl status tgbot` и `sudo journalctl -u tgbot -n 50` |
| VM остановилась | Compute Engine -> нажать **Запустить** |
| Не пишет в Google Sheets | Проверить `credentials.json` и доступ к таблице (раздел 5) |
| Пришел алерт о расходах | Проверить регион (US) и тип машины (e2-micro) |

---

**Репозиторий:** https://github.com/dynyaa/tgbotasl
