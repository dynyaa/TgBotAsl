"""
Точка входа для запуска бота.
Запуск: python run.py
"""

import asyncio
import sys

from bot.main import main


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен.")
        sys.exit(0)
