import requests
import settings
from datetime import date


def send_telegram_alert(message: str) -> None:
    """Отправляет сообщение в Telegram, используя настройки из settings.py."""
    if not settings.BOT_TOKEN or not settings.CHAT_ID:
        print("Отправка в Telegram пропущена: BOT_TOKEN или CHAT_ID не настроены.")
        return

    url = f"https://api.telegram.org/bot{settings.BOT_TOKEN}/sendMessage"
    payload = {"chat_id": settings.CHAT_ID, "text": message}

    try:
        # Добавляем таймаут для предотвращения "зависания" скрипта
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        print("Уведомление успешно отправлено.")
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при отправке уведомления: {e}")


def report_findings(problem_reports: list[str], stats: dict):
    """
    Формирует и отправляет отчет о проблемах, если они есть,
    и обновляет статистику.
    """
    # Увеличиваем счетчик проблем на количество новых инцидентов
    stats["problems_today"] += len(problem_reports)

    print("\n--- Обнаружены проблемы ---")
    alert_message = "Обнаружены проблемы с клиентами ZeroTier:\n\n" + "\n".join(
        problem_reports
    )
    print(alert_message)

    print("\nОтправка уведомления в Telegram...")
    send_telegram_alert(alert_message)


def send_daily_report(stats: dict):
    """Отправляет ежедневный отчет о работе скрипта и статистике."""
    report_date = stats.get("last_report_date", str(date.today()))
    message = (
        f"🌙 Ежедневный отчет за {report_date}:\n\n"
        f"✅ Скрипт мониторинга ZeroTier работает в штатном режиме.\n"
        f"📈 Проверок за день: {stats.get('checks_today', 0)}\n"
        f"⚠️ Выявлено инцидентов: {stats.get('problems_today', 0)}"
    )
    print("\n--- Отправка ежедневного отчета ---")
    print(message)
    send_telegram_alert(message)


def send_startup_notification():
    """Отправляет уведомление о запуске скрипта."""
    message = "🚀 Мониторинг ZeroTier успешно запущен."
    print("\n" + message)
    send_telegram_alert(message)
