import os
import json
import time
import sys
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()


def _exit_with_error(message: str):
    """Выводит сообщение о критической ошибке и завершает работу скрипта."""
    print(f"\nКРИТИЧЕСКАЯ ОШИБКА: {message}")
    print("Пожалуйста, исправьте конфигурацию в файле .env и перезапустите скрипт.")
    # Добавляем паузу, чтобы пользователь успел прочитать ошибку в консоли
    time.sleep(15)
    sys.exit(1)


# --- Загрузка и валидация конфигурации из .env файла ---

# Загрузка сетей ZeroTier из JSON-строки
ZEROTIER_NETWORKS_JSON = os.getenv("ZEROTIER_NETWORKS_JSON")
ZEROTIER_NETWORKS = []
if ZEROTIER_NETWORKS_JSON:
    try:
        ZEROTIER_NETWORKS = json.loads(ZEROTIER_NETWORKS_JSON)
        if not isinstance(ZEROTIER_NETWORKS, list):
            raise ValueError("JSON должен быть списком (массивом).")
        # Дополнительная проверка структуры
        for network in ZEROTIER_NETWORKS:
            if (
                not isinstance(network, dict)
                or "token" not in network
                or "network_id" not in network
            ):
                raise ValueError(
                    "Каждый элемент списка должен быть словарем с ключами 'token' и 'network_id'."
                )
    except (json.JSONDecodeError, ValueError) as e:
        _exit_with_error(f"Неверный формат ZEROTIER_NETWORKS_JSON в .env файле. {e}")
else:
    _exit_with_error("Переменная ZEROTIER_NETWORKS_JSON не найдена в .env файле.")

# Загрузка ID участников из строки, разделенной запятыми
MEMBER_IDS_CSV = os.getenv("MEMBER_IDS_CSV")
if MEMBER_IDS_CSV:
    MEMBER_IDS = [item.strip() for item in MEMBER_IDS_CSV.split(",")]
else:
    _exit_with_error("Переменная MEMBER_IDS_CSV не найдена в .env файле.")

# API и Telegram токены
API_URL = "https://api.zerotier.com/api/v1/"
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# --- Конфигурация файлов, порогов и интервалов ---
STATE_FILE = "alert_state.json"
STATS_FILE = "daily_stats.json"

# Уровни оповещений об офлайне.
OFFLINE_THRESHOLDS = {
    "1h": {"seconds": 3600, "message": "🆘 {name}: офлайн более 1 часа!", "level": 3},
    "15m": {"seconds": 900, "message": "🚨 {name}: офлайн более 15 минут!", "level": 2},
    "5m": {"seconds": 300, "message": "⚠️ {name}: офлайн более 5 минут.", "level": 1},
}

# Порог, после которого устройство считается онлайн (в секундах)
if "5m" not in OFFLINE_THRESHOLDS:
    _exit_with_error("В OFFLINE_THRESHOLDS отсутствует обязательный ключ '5m'.")
ONLINE_THRESHOLD_SECONDS = OFFLINE_THRESHOLDS["5m"]["seconds"]

# Интервал проверки
try:
    CHECK_INTERVAL_SECONDS = int(os.getenv("CHECK_INTERVAL_SECONDS", 300))
    if CHECK_INTERVAL_SECONDS <= 0:
        print(
            "Интервал проверки должен быть положительным числом. Используется значение по умолчанию: 300 секунд."
        )
        CHECK_INTERVAL_SECONDS = 300
except (ValueError, TypeError):
    print(
        "Неверный формат CHECK_INTERVAL_SECONDS в .env. Используется значение по умолчанию: 300 секунд."
    )
    CHECK_INTERVAL_SECONDS = 300

# --- Настройки для повторных запросов к API ---
API_RETRY_ATTEMPTS = 3
API_RETRY_DELAY_SECONDS = 5
