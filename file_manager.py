import os
import json
from datetime import date


def load_state(filepath: str) -> dict:
    """Загружает состояние оповещений из JSON-файла."""
    if not os.path.exists(filepath):
        return {}
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(
            f"Ошибка загрузки файла состояния {filepath}: {e}. Начинаем с чистого состояния."
        )
        return {}


def save_state(filepath: str, state: dict) -> None:
    """Сохраняет состояние оповещений в JSON-файл."""
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=4, ensure_ascii=False)
    except IOError as e:
        print(f"Ошибка сохранения файла состояния {filepath}: {e}")


def load_stats(filepath: str) -> dict:
    """Загружает статистику из JSON-файла."""
    default_stats = {
        "last_report_date": str(date.today()),
        "checks_today": 0,
        "problems_today": 0,
    }
    if not os.path.exists(filepath):
        return default_stats
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        print(
            f"Ошибка чтения файла статистики {filepath}. Используются значения по умолчанию."
        )
        return default_stats


def save_stats(filepath: str, stats: dict) -> None:
    """Сохраняет статистику в JSON-файл."""
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=4, ensure_ascii=False)
    except IOError as e:
        print(f"Ошибка сохранения файла статистики {filepath}: {e}")
