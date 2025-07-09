"""Модуль для отправки уведомлений и отчетов о состоянии ZeroTier в Telegram."""

from datetime import date
import settings
import http_client
from models import ProblematicMember
from utils import get_project_version


def send_telegram_alert(message: str) -> None:
    """Отправляет сообщение в Telegram с несколькими попытками в случае сбоя."""
    if not settings.BOT_TOKEN or not settings.CHAT_ID:
        print(settings.t("telegram_sending_skipped"))
        return

    url = f"https://api.telegram.org/bot{settings.BOT_TOKEN}/sendMessage"
    payload = {"chat_id": settings.CHAT_ID, "text": message}

    error_log_template = settings.t("telegram_sending_error", e="{e}")

    response, _ = http_client.make_request(
        "POST", url, error_log_template, json=payload
    )

    if response:
        print(settings.t("telegram_notification_sent"))
    else:
        print(settings.t("telegram_sending_error", e="All attempts failed."))


def report_findings(problem_reports: list[str], stats: dict):
    """
    Формирует и отправляет отчет о проблемах, если они есть,
    и обновляет статистику.
    """
    # Увеличиваем счетчик проблем на количество новых инцидентов
    stats["problems_today"] += len(problem_reports)

    print(f"\n{settings.t('problems_detected_header')}")
    alert_message = settings.t("problems_report_header") + "\n".join(problem_reports)
    print(alert_message)

    print(f"\n{settings.t('sending_telegram_notification')}")
    send_telegram_alert(alert_message)


def send_daily_report(stats: dict, problematic_members: list[ProblematicMember]):
    """Отправляет ежедневный отчет о работе скрипта и статистике."""
    report_date = stats.get("last_report_date", str(date.today()))
    last_check = stats.get("last_check_datetime", "N/A")
    message = (
        f"{settings.t('daily_report_title', date=report_date)}"
        f"{settings.t('daily_report_status_ok')}"
        f"{settings.t('daily_report_checks', checks=stats.get('checks_today', 0))}"
        f"{settings.t('daily_report_incidents', problems=stats.get('problems_today', 0))}"
        f"{settings.t('daily_report_last_check', last_check=last_check)}"
    )

    if problematic_members:
        problem_details = settings.t("daily_report_problematic_members_header")
        for member in problematic_members:
            problem_details += settings.t(
                "daily_report_problematic_member_line",
                name=member.name,
                count=member.problems_count,
            )
        message += problem_details

    print(f"\n{settings.t('sending_daily_report')}")
    print(message)
    send_telegram_alert(message)


def send_startup_notification():
    """Отправляет уведомление о запуске скрипта."""
    message = settings.t("startup_notification", version=get_project_version())
    print("\n" + message)
    send_telegram_alert(message)
