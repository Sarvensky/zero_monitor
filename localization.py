"""
Модуль для хранения всех текстовых строк и их переводов.
"""

# Словарь, содержащий все строки для всех поддерживаемых языков.
# Ключи верхнего уровня - это коды языков (например, 'ru', 'en').
# Вложенные ключи - это идентификаторы строк, используемые в коде.
STRINGS = {
    "ru": {
        # Общие
        "critical_error": "КРИТИЧЕСКАЯ ОШИБКА: {message}",
        "fix_env_and_restart": "Пожалуйста, исправьте конфигурацию в файле .env и перезапустите скрипт.",
        "attempt_info": "Попытка {attempt}/{total}:",
        "retry_in_seconds": "Повторная попытка через {delay} сек...",
        "all_attempts_failed_with_error": "Все попытки исчерпаны. Последняя ошибка: {error}",
        "all_attempts_failed": "Все попытки исчерпаны.",
        # settings.py
        "json_must_be_list": "JSON должен быть списком (массивом).",
        "json_must_be_dict": "Каждый элемент списка должен быть словарем с ключами 'token' и 'network_id'.",
        "invalid_json_format": "Неверный формат ZEROTIER_NETWORKS_JSON в .env файле. {e}",
        "zt_networks_json_not_found": "Переменная ZEROTIER_NETWORKS_JSON не найдена в .env файле.",
        "member_ids_csv_not_found": "Переменная MEMBER_IDS_CSV не найдена в .env файле.",
        "offline_threshold_5m_missing": "В OFFLINE_THRESHOLDS отсутствует обязательный ключ '5m'.",
        "interval_must_be_positive": (
            "Интервал проверки должен быть положительным числом. "
            "Используется значение по умолчанию: 300 секунд."
        ),
        "invalid_interval_format": (
            "Неверный формат CHECK_INTERVAL_SECONDS в .env. "
            "Используется значение по умолчанию: 300 секунд."
        ),
        # api_client.py
        "getting_members_info": "Получение информации о членах сети ZeroTier...",
        "error_getting_members": "Ошибка при получении участников сети {net_id}: {e}",
        "failed_to_get_members_for_network": "Не удалось получить участников для сети {net_id}",
        "alert_failed_to_get_members": (
            "⛔ Не удалось получить участников сети {net_id} после {attempts} попыток. "
            "Последняя ошибка: {error}"
        ),
        "error_getting_latest_version": "Ошибка при получении последней версии ZeroTier: {e}",
        "alert_failed_to_get_latest_version": (
            "⛔ Не удалось получить последнюю версию ZeroTier после {attempts} попыток. "
            "Последняя ошибка: {error}"
        ),
        "using_fallback_version": "Используется версия по умолчанию: {version}",
        "using_db_version": "Используется версия из базы данных: {version}",
        "zt_version_db_updated": "Версия ZeroTier в базе данных обновлена на {version}",
        # checker.py
        "ping_command_not_found": "ОШИБКА: Команда 'ping' не найдена. Невозможно проверить хост {ip}.",
        "version_report_old": "🔧 {name}: старая версия ({version})",
        "version_report_updated": "✅ {name}: версия обновлена до актуальной ({version})",
        "member_never_online": "❓ {name}: ни разу не был в сети.",
        "anomaly_detected": (
            "АНАЛИЗ: Обнаружен аномальный скачок 'lastSeen' для {name}. "
            "API: {api_s} сек, Предыдущее: {prev_s} сек. "
            "Используется расчетное значение: {calc_s} сек."
        ),
        "last_seen_calculated": "~{seconds} сек. назад (расчетное)",
        "last_seen_normal": "{seconds} сек. назад",
        "device_back_online": "✅ Устройство {name} снова в сети.",
        "member_back_online_report": "✅ {name}: снова в сети.",
        "checking_ping_for_offline_node": "АНАЛИЗ: Узел {name} офлайн. Проверяю пинг до {ip}...",
        "ping_success_report": "\n  (💡 Пинг до {ip} проходит. Возможен сбой контроллера.)",
        "ping_fail_report": "\n  (❗️ Пинг до {ip} не проходит. Узел недоступен.)",
        "no_ip_for_ping": "АНАЛИЗ: У узла {name} нет IP-адреса для проверки пинга.",
        "check_result_log": "ID: {id}, Имя: {name}, Версия: {version} [{status}], Онлайн: {online_str}",
        "offline_level1_message": "⚠️ {name}: офлайн более 5 минут.",
        "offline_level2_message": "🚨 {name}: офлайн более 15 минут!",
        "offline_level3_message": "🆘 {name}: офлайн более 1 часа!",
        # database_manager.py
        "column_added_to_table": "Столбец '{column}' добавлен в таблицу '{table}'.",
        "db_initialized": "База данных инициализирована, сохраненные состояния 'lastSeen' сброшены.",
        "daily_counters_reset": "Счетчики проблем для всех узлов сброшены.",
        # send_to_chat.py
        "telegram_sending_skipped": "Отправка в Telegram пропущена: BOT_TOKEN или CHAT_ID не настроены.",
        "telegram_notification_sent": "Уведомление успешно отправлено.",
        "telegram_sending_error": "Ошибка при отправке уведомления в Telegram: {e}",
        "problems_detected_header": "--- Обнаружены проблемы ---",
        "problems_report_header": "🔎 Обнаружены проблемы с клиентами ZeroTier:\n\n",
        "sending_telegram_notification": "Отправка уведомления в Telegram...",
        "daily_report_title": "🌙 Ежедневный отчет за {date}:\n\n",
        "daily_report_status_ok": "✅ Скрипт мониторинга ZeroTier работает в штатном режиме.\n",
        "daily_report_checks": "📈 Проверок за день: {checks}\n",
        "daily_report_incidents": "⚠️ Выявлено инцидентов: {problems}\n",
        "daily_report_last_check": "🕒 Последняя проверка: {last_check}",
        "daily_report_problematic_members_header": "\n\n📊 Статистика по узлам с проблемами:",
        "daily_report_problematic_member_line": "\n  - {name}: {count} инцидентов",
        "sending_daily_report": "--- Отправка ежедневного отчета ---",
        "startup_notification": "🚀 Мониторинг ZeroTier (v{version}) успешно запущен.",
        "stop_notification": "🚧 Мониторинг ZeroTier остановлен",
        # main.py
        "current_datetime": "Дата и время сейчас: {check_time_str}",
        "latest_zt_version": "Актуальная версия ZeroTier: {latest_version}",
        "get_members_failed_skipping": "Не удалось получить информацию об участниках сети. Пропуск проверки.",
        "check_results_header": "--- Результаты проверки ---",
        "no_new_problems": "Новых проблем или изменений статуса не обнаружено.",
        "invalid_report_date_in_db": "Некорректная дата последнего отчета в БД. Используется текущая дата.",
        "new_day_started": "--- Наступил новый день ({current_date}). Отправка отчета за {last_report_date}. ---",
        "unexpected_error": "--- Произошла непредвиденная ошибка: {e} ---",
        "pause_before_next_check": "--- Пауза {minutes} минут до следующей проверки ---",
        "script_stopped_by_user": "\nСкрипт остановлен пользователем.",
    },
    "en": {
        # Common
        "critical_error": "CRITICAL ERROR: {message}",
        "fix_env_and_restart": "Please fix the configuration in the .env file and restart the script.",
        "attempt_info": "Attempt {attempt}/{total}:",
        "retry_in_seconds": "Retrying in {delay} sec...",
        "all_attempts_failed_with_error": "All attempts have been exhausted. Last error: {error}",
        "all_attempts_failed": "All attempts have been exhausted.",
        # settings.py
        "json_must_be_list": "JSON must be a list (array).",
        "json_must_be_dict": "Each list item must be a dictionary with 'token' and 'network_id' keys.",
        "invalid_json_format": "Invalid ZEROTIER_NETWORKS_JSON format in .env file. {e}",
        "zt_networks_json_not_found": "ZEROTIER_NETWORKS_JSON variable not found in .env file.",
        "member_ids_csv_not_found": "MEMBER_IDS_CSV variable not found in .env file.",
        "offline_threshold_5m_missing": "OFFLINE_THRESHOLDS is missing the required '5m' key.",
        "interval_must_be_positive": (
            "Check interval must be a positive number. "
            "Using default value: 300 seconds."
        ),
        "invalid_interval_format": (
            "Invalid CHECK_INTERVAL_SECONDS format in .env. "
            "Using default value: 300 seconds."
        ),
        # api_client.py
        "getting_members_info": "Getting information about ZeroTier network members...",
        "error_getting_members": "Error getting members for network {net_id}: {e}",
        "failed_to_get_members_for_network": "Failed to get members for network {net_id}",
        "alert_failed_to_get_members": (
            "⛔ Failed to get members for network {net_id} after {attempts} attempts. "
            "Last error: {error}"
        ),
        "error_getting_latest_version": "Error getting the latest ZeroTier version: {e}",
        "alert_failed_to_get_latest_version": (
            "⛔ Failed to get the latest ZeroTier version after {attempts} attempts. "
            "Last error: {error}"
        ),
        "using_fallback_version": "Using fallback version: {version}",
        "using_db_version": "Using version from database: {version}",
        "zt_version_db_updated": "ZeroTier version in database updated to {version}",
        # checker.py
        "ping_command_not_found": "ERROR: 'ping' command not found. Cannot check host {ip}.",
        "version_report_old": "🔧 {name}: outdated version ({version})",
        "version_report_updated": "✅ {name}: version updated to the latest ({version})",
        "member_never_online": "❓ {name}: has never been online.",
        "anomaly_detected": (
            "ANALYSIS: Anomalous 'lastSeen' jump detected for {name}. "
            "API: {api_s}s, Previous: {prev_s}s. Using calculated value: {calc_s}s."
        ),
        "last_seen_calculated": "~{seconds}s ago (calculated)",
        "last_seen_normal": "{seconds}s ago",
        "device_back_online": "✅ Device {name} is back online.",
        "member_back_online_report": "✅ {name}: is back online.",
        "checking_ping_for_offline_node": "ANALYSIS: Node {name} is offline. Checking ping to {ip}...",
        "ping_success_report": "\n  (💡 Ping to {ip} is successful. Controller might be down.)",
        "ping_fail_report": "\n  (❗️ Ping to {ip} is failing. Node is unreachable.)",
        "no_ip_for_ping": "ANALYSIS: Node {name} has no IP address for ping check.",
        "check_result_log": "ID: {id}, Name: {name}, Version: {version} [{status}], Online: {online_str}",
        "offline_level1_message": "⚠️ {name}: offline for more than 5 minutes.",
        "offline_level2_message": "🚨 {name}: offline for more than 15 minutes!",
        "offline_level3_message": "🆘 {name}: offline for more than 1 hour!",
        # database_manager.py
        "column_added_to_table": "Column '{column}' added to table '{table}'.",
        "db_initialized": "Database initialized, saved 'lastSeen' states have been reset.",
        "daily_counters_reset": "Daily problem counters for all nodes have been reset.",
        # send_to_chat.py
        "telegram_sending_skipped": "Telegram sending skipped: BOT_TOKEN or CHAT_ID is not configured.",
        "telegram_notification_sent": "Notification sent successfully.",
        "telegram_sending_error": "Error sending notification to Telegram: {e}",
        "problems_detected_header": "--- Problems Detected ---",
        "problems_report_header": "🔎 Problems detected with ZeroTier clients:\n\n",
        "sending_telegram_notification": "Sending notification to Telegram...",
        "daily_report_title": "🌙 Daily report for {date}:\n\n",
        "daily_report_status_ok": "✅ ZeroTier monitoring script is running normally.\n",
        "daily_report_checks": "📈 Checks today: {checks}\n",
        "daily_report_incidents": "⚠️ Incidents detected: {problems}\n",
        "daily_report_last_check": "🕒 Last check: {last_check}",
        "daily_report_problematic_members_header": "\n\n📊 Statistics for nodes with problems:",
        "daily_report_problematic_member_line": "\n  - {name}: {count} incidents",
        "sending_daily_report": "--- Sending daily report ---",
        "startup_notification": "🚀 ZeroTier Monitor (v{version}) started successfully.",
        "stop_notification": "🚧 *ZeroTier Monitor stopped*",
        # main.py
        "current_datetime": "Current date and time: {check_time_str}",
        "latest_zt_version": "Latest ZeroTier version: {latest_version}",
        "get_members_failed_skipping": "Failed to get network member information. Skipping check.",
        "check_results_header": "--- Check Results ---",
        "no_new_problems": "No new problems or status changes detected.",
        "invalid_report_date_in_db": "Invalid last report date in DB. Using current date.",
        "new_day_started": "--- New day has started ({current_date}). Sending report for {last_report_date}. ---",
        "unexpected_error": "--- An unexpected error occurred: {e} ---",
        "pause_before_next_check": "--- Pausing for {minutes} minutes until the next check ---",
        "script_stopped_by_user": "\nScript stopped by user.",
    },
}


class Translator:
    """
    Класс для управления переводами.
    Инициализируется с указанием языка и предоставляет метод `t` для получения строк.
    """

    def __init__(self, language: str):
        """
        Инициализирует переводчик.
        Args:
            language: Код языка ('ru', 'en', и т.д.).
        """
        # Устанавливаем язык, по умолчанию 'ru', если указанный язык не найден
        if language.lower() in STRINGS:
            self.lang = language.lower()
        else:
            # В случае, если язык не поддерживается, выводим сообщение на обоих языках
            # для максимальной понятности.
            print(
                f"Unsupported language '{language}'. Using 'ru'. / Неподдерживаемый язык '{language}'. Используется 'ru'."
            )
            self.lang = "ru"

    def t(self, key: str, **kwargs) -> str:
        """
        Возвращает строку по ключу для текущего языка.
        Поддерживает форматирование с помощью именованных аргументов.

        Args:
            key: Ключ строки в словаре STRINGS.
            **kwargs: Аргументы для форматирования строки.

        Returns:
            Переведенная и отформатированная строка.
            Если ключ не найден, возвращает сам ключ.
        """
        # Получаем строку из словаря, если ключа нет - возвращаем сам ключ
        string_template = STRINGS.get(self.lang, {}).get(key, key)
        # Если строка была разбита на части, "склеиваем" ее
        if isinstance(string_template, tuple):
            string_template = "".join(string_template)

        if kwargs:
            return string_template.format(**kwargs)
        return string_template
