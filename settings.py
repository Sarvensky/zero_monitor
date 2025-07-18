"""Модуль с настройками и конфигурацией для мониторинга ZeroTier."""

import os
from dotenv import load_dotenv
from localization import Translator
import utils

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

# --- Информация о версии ---
# Версия по умолчанию, если git недоступен или это не git-репозиторий
PROJECT_VERSION_FALLBACK = "1.4"
# Версия ZeroTier по умолчанию, если не удается получить с GitHub или из БД
ZT_FALLBACK_VERSION = "1.14.2"
# Получаем версию проекта динамически при запуске
PROJECT_VERSION = utils.get_project_version(PROJECT_VERSION_FALLBACK)

# --- Загрузка и валидация конфигурации из .env файла ---
ZEROTIER_NETWORKS = utils.load_zt_networks(t)
MEMBER_IDS = utils.load_member_ids(t)

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

# Пороги для определения офлайн-статуса.
# Ключи - для удобства, level - для сравнения, message_key - для отчета.
OFFLINE_THRESHOLDS = {
    "1h": {"seconds": 3600, "message_key": "offline_level3_message", "level": 3},
    "15m": {"seconds": 900, "message_key": "offline_level2_message", "level": 2},
    "5m": {"seconds": 300, "message_key": "offline_level1_message", "level": 1},
}

# Валидация: обязательное наличие порога '5m', так как он используется
# для определения статуса "онлайн" и сброса алертов.
if "5m" not in OFFLINE_THRESHOLDS:
    # Эта проверка больше для целостности, но важна для логики работы.
    utils.exit_with_error(t("offline_threshold_5m_missing"), t)

# Порог, после которого устройство считается онлайн (в секундах)
ONLINE_THRESHOLD_SECONDS = OFFLINE_THRESHOLDS["5m"]["seconds"]

CHECK_INTERVAL_SECONDS = utils.load_check_interval(t)

# --- Настройки для повторных запросов к API ---
API_RETRY_ATTEMPTS = 3
API_RETRY_DELAY_SECONDS = 5
API_TIMEOUT_SECONDS = 10  # Таймаут для API запросов в секундах
