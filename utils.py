"""Общие вспомогательные утилиты."""

import subprocess
from datetime import datetime


def get_project_version() -> str:
    """
    Получает версию проекта из Git.
    Использует 'git describe --tags --always' для получения тега или хеша коммита.
    Возвращает "неизвестно" в случае ошибки (например, если это не git-репозиторий).
    """
    try:
        command = ["git", "describe", "--tags", "--always"]
        # check=True вызовет исключение, если команда завершится с ошибкой
        result = subprocess.run(
            command, capture_output=True, text=True, check=True, encoding="utf-8"
        )
        # Убираем возможные переводы строк в конце вывода
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Обрабатываем случай, когда git не установлен или это не git-репозиторий
        return "неизвестно"


def now_datetime() -> str:
    """Возвращает текущую дату и время в строке формата YYYY-MM-DD HH:MM:SS."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_seconds_since(last_online: int | None, time_ms: int | None) -> int:
    """
    Вычисляет разницу в секундах между текущим временем (time_ms)
    и временем последнего онлайна (last_online).
    Оба значения должны быть в миллисекундах.
    Возвращает целое число секунд или -1, если данные некорректны.
    """
    if last_online is None or time_ms is None:
        return -1
    diff_seconds = abs(time_ms - last_online) / 1000
    return int(diff_seconds)
