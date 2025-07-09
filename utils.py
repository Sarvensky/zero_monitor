"""Общие вспомогательные утилиты."""

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from typing import Callable, NoReturn


def exit_with_error(message: str, t: Callable) -> NoReturn:
    """Выводит сообщение о критической ошибке и завершает работу скрипта."""
    print(f"\n{t('critical_error', message=message)}")
    print(t("fix_env_and_restart"))
    time.sleep(15)
    sys.exit(1)


def get_project_version(fallback: str) -> str:
    """
    Получает версию проекта из Git.
    Использует 'git describe --tags --always' и форматирует результат.
    Возвращает версию из настроек в случае ошибки.
    """
    try:
        project_root = os.path.dirname(os.path.abspath(__file__))
        command = ["git", "describe", "--tags", "--always"]
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            encoding="utf-8",
            cwd=project_root,
        )
        raw_version = result.stdout.strip()
        # Заменяем первый дефис на точку для более красивого вида.
        # Например, '1.1-1-g123abc' превратится в '1.1.1-g123abc'.
        return raw_version.replace("-", ".", 1)
    except (subprocess.CalledProcessError, FileNotFoundError):
        return fallback


def load_zt_networks(t: Callable) -> list[dict]:
    """Загружает и валидирует сети ZeroTier из переменной окружения."""
    networks_json = os.getenv("ZEROTIER_NETWORKS_JSON")
    if not networks_json:
        exit_with_error(t("zt_networks_json_not_found"), t)

    try:
        networks = json.loads(networks_json)
        if not isinstance(networks, list):
            raise ValueError(t("json_must_be_list"))
        for network in networks:
            if (
                not isinstance(network, dict)
                or "token" not in network
                or "network_id" not in network
            ):
                raise ValueError(t("json_must_be_dict"))
        return networks
    except (json.JSONDecodeError, ValueError) as e:
        exit_with_error(t("invalid_json_format", e=e), t)
    return []  # Недостижимо, но нужно для линтера


def load_member_ids(t: Callable) -> list[str]:
    """Загружает ID участников из переменной окружения."""
    member_ids_csv = os.getenv("MEMBER_IDS_CSV")
    if not member_ids_csv:
        exit_with_error(t("member_ids_csv_not_found"), t)
    return [item.strip() for item in member_ids_csv.split(",")]


def load_check_interval(t: Callable) -> int:
    """Загружает и валидирует интервал проверки из переменной окружения."""
    default_interval = 300
    try:
        interval = int(os.getenv("CHECK_INTERVAL_SECONDS", str(default_interval)))
        if interval <= 0:
            print(t("interval_must_be_positive"))
            return default_interval
        return interval
    except (ValueError, TypeError):
        print(t("invalid_interval_format"))
        return default_interval


def load_offline_thresholds(t: Callable) -> dict:
    """Определяет и валидирует пороги для определения офлайн-статуса."""
    thresholds = {
        "1h": {"seconds": 3600, "message_key": "offline_level3_message", "level": 3},
        "15m": {"seconds": 900, "message_key": "offline_level2_message", "level": 2},
        "5m": {"seconds": 300, "message_key": "offline_level1_message", "level": 1},
    }
    if "5m" not in thresholds:
        # Эта проверка больше для целостности, т.к. словарь определен здесь же.
        exit_with_error(t("offline_threshold_5m_missing"), t)
    return thresholds


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
