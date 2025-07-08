"""Модуль с настройками и конфигурацией для мониторинга ZeroTier."""

import os
import json
import time
import sys
from dotenv import load_dotenv
from localization import Translator

# Загружаем переменные окружения из .env файла
load_dotenv()

# --- Языковые настройки ---
# Загрузка языка из .env, по умолчанию 'ru'
# LANGUAGE=RU или LANGUAGE=EN
LANGUAGE = os.getenv("LANGUAGE", "ru").lower()

# --- Инициализация локализации ---
# Создаем глобальный экземпляр переводчика, который будет доступен
# во всем проекте через импорт `from settings import t`.
# Это централизует управление языком.
t = Translator(LANGUAGE).t


def _exit_with_error(message: str):
    """Выводит сообщение о критической ошибке и завершает работу скрипта."""
    # Используем переводчик для вывода сообщений
    print(f"\n{t('critical_error', message=message)}")
    print(t("fix_env_and_restart"))
    # Добавляем паузу, чтобы пользователь успел прочитать ошибку в консоли
    time.sleep(15)
    sys.exit(1)


# --- Информация о версии ---
# Получаем версию проекта из Git при запуске
PROJECT_VERSION = "1.3"

# --- Загрузка и валидация конфигурации из .env файла ---

# Загрузка сетей ZeroTier из JSON-строки
ZEROTIER_NETWORKS_JSON = os.getenv("ZEROTIER_NETWORKS_JSON")
ZEROTIER_NETWORKS = []
if ZEROTIER_NETWORKS_JSON:
    try:
        ZEROTIER_NETWORKS = json.loads(ZEROTIER_NETWORKS_JSON)
        if not isinstance(ZEROTIER_NETWORKS, list):
            raise ValueError(t("json_must_be_list"))
        # Дополнительная проверка структуры
        for network in ZEROTIER_NETWORKS:
            if (
                not isinstance(network, dict)
                or "token" not in network
                or "network_id" not in network
            ):
                raise ValueError(t("json_must_be_dict"))
    except (json.JSONDecodeError, ValueError) as e:
        _exit_with_error(t("invalid_json_format", e=e))
else:
    _exit_with_error(t("zt_networks_json_not_found"))

# Загрузка ID участников из строки, разделенной запятыми
MEMBER_IDS_CSV = os.getenv("MEMBER_IDS_CSV")
if MEMBER_IDS_CSV:
    MEMBER_IDS = [item.strip() for item in MEMBER_IDS_CSV.split(",")]
else:
    _exit_with_error(t("member_ids_csv_not_found"))

# API и Telegram токены
API_URL = "https://api.zerotier.com/api/v1/"
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# --- Конфигурация файлов, порогов и интервалов ---
DB_FILE = "monitor_state.db"  # Файл базы данных SQLite

# Порог для определения аномального скачка времени офлайна (в секундах).
# Если 'lastSeen' от API больше, чем (предыдущее значение + интервал проверки + этот порог),
# то считаем это аномалией и используем расчетное значение.
# Это нужно для сглаживания редких выбросов в ответах API ZeroTier.
LAST_SEEN_ANOMALY_THRESHOLD_SECONDS = 200

# Уровни оповещений об офлайне.
OFFLINE_THRESHOLDS = {
    "1h": {"seconds": 3600, "message_key": "offline_level3_message", "level": 3},
    "15m": {"seconds": 900, "message_key": "offline_level2_message", "level": 2},
    "5m": {"seconds": 300, "message_key": "offline_level1_message", "level": 1},
}

# Порог, после которого устройство считается онлайн (в секундах)
if "5m" not in OFFLINE_THRESHOLDS:
    _exit_with_error(t("offline_threshold_5m_missing"))
ONLINE_THRESHOLD_SECONDS = OFFLINE_THRESHOLDS["5m"]["seconds"]

# Интервал проверки
try:
    CHECK_INTERVAL_SECONDS = int(os.getenv("CHECK_INTERVAL_SECONDS", "300"))
    if CHECK_INTERVAL_SECONDS <= 0:
        print(t("interval_must_be_positive"))
        CHECK_INTERVAL_SECONDS = 300
except (ValueError, TypeError):
    print(t("invalid_interval_format"))
    CHECK_INTERVAL_SECONDS = 300

# --- Настройки для повторных запросов к API ---
API_RETRY_ATTEMPTS = 3
API_RETRY_DELAY_SECONDS = 5
