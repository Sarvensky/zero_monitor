"""Модуль для отправки уведомлений и отчетов о состоянии ZeroTier в Telegram."""

from datetime import date
import time
import requests
import settings


def send_telegram_alert(message: str) -> None:
    """Отправляет сообщение в Telegram с несколькими попытками в случае сбоя."""
    if not settings.BOT_TOKEN or not settings.CHAT_ID:
        print("Отправка в Telegram пропущена: BOT_TOKEN или CHAT_ID не настроены.")
        return

    url = f"https://api.telegram.org/bot{settings.BOT_TOKEN}/sendMessage"
    payload = {"chat_id": settings.CHAT_ID, "text": message}

    for attempt in range(settings.API_RETRY_ATTEMPTS):
        try:
            # Добавляем таймаут для предотвращения "зависания" скрипта
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            print("Уведомление успешно отправлено.")
            return  # Выходим из функции при успехе
        except requests.exceptions.RequestException as e:
            print(
                f"Попытка {attempt + 1}/{settings.API_RETRY_ATTEMPTS}: "
                f"Ошибка при отправке уведомления в Telegram: {e}"
            )
            if attempt < settings.API_RETRY_ATTEMPTS - 1:
                print(
                    f"Повторная попытка через {settings.API_RETRY_DELAY_SECONDS} сек..."
                )
                time.sleep(settings.API_RETRY_DELAY_SECONDS)
            else:
                print("Все попытки отправки уведомления исчерпаны.")


def report_findings(problem_reports: list[str], stats: dict):
    """
    Формирует и отправляет отчет о проблемах, если они есть,
    и обновляет статистику.
    """
    # Увеличиваем счетчик проблем на количество новых инцидентов
    stats["problems_today"] += len(problem_reports)

    print("\n--- Обнаружены проблемы ---")
    alert_message = "🔎 Обнаружены проблемы с клиентами ZeroTier:\n\n" + "\n".join(
        problem_reports
    )
    print(alert_message)

    print("\nОтправка уведомления в Telegram...")
    send_telegram_alert(alert_message)


def send_daily_report(stats: dict, problematic_members: list):
    """Отправляет ежедневный отчет о работе скрипта и статистике."""
    report_date = stats.get("last_report_date", str(date.today()))
    last_check = stats.get("last_check_datetime", "н/д")
    message = (
        f"🌙 Ежедневный отчет за {report_date}:\n\n"
        f"✅ Скрипт мониторинга ZeroTier работает в штатном режиме.\n"
        f"📈 Проверок за день: {stats.get('checks_today', 0)}\n"
        f"⚠️ Выявлено инцидентов: {stats.get('problems_today', 0)}\n"
        f"🕒 Последняя проверка: {last_check}"
    )

    if problematic_members:
        problem_details = "\n\n📊 Статистика по узлам с проблемами:"
        for member in problematic_members:
            problem_details += (
                f"\n  - {member['name']}: {member['problems_count']} инцидентов"
            )
        message += problem_details

    print("\n--- Отправка ежедневного отчета ---")
    print(message)
    send_telegram_alert(message)


def send_startup_notification():
    """Отправляет уведомление о запуске скрипта."""
    message = (
        f"🚀 Мониторинг ZeroTier (версия: {settings.PROJECT_VERSION}) успешно запущен."
    )
    print("\n" + message)
    send_telegram_alert(message)
