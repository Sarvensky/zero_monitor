"""Модуль для отправки уведомлений и отчетов о состоянии ZeroTier в Telegram."""

from datetime import date
import settings
from http_client import ApiClientError, make_request
from models import ProblematicMember


def send_telegram_alert(message: str) -> None:
    """Отправляет сообщение в Telegram с несколькими попытками в случае сбоя."""
    if not settings.BOT_TOKEN or not settings.CHAT_ID:
        print(settings.t("telegram_sending_skipped"))
        return

    url = f"https://api.telegram.org/bot{settings.BOT_TOKEN}/sendMessage"
    payload = {"chat_id": settings.CHAT_ID, "text": message}

    error_log_template = settings.t("telegram_sending_error", e="{e}")

    try:
        make_request("POST", url, error_log_template, json=payload)
        print(settings.t("telegram_notification_sent"))
    except ApiClientError as e:
        # Теперь мы логируем настоящую причину сбоя, а не просто "все попытки провалились"
        print(settings.t("telegram_sending_error", e=e))


def report_findings(problem_reports: list[str]):
    """Формирует и отправляет отчет о проблемах, если они есть."""
    print(f"\n{settings.t('problems_detected_header')}")
    alert_message = settings.t("problems_report_header") + "\n".join(problem_reports)
    print(alert_message)

    print(f"\n{settings.t('sending_telegram_notification')}")
    send_telegram_alert(alert_message)


def _build_daily_report_message(
    stats: dict, problematic_members: list[ProblematicMember]
) -> str:
    """Собирает текст для ежедневного отчета."""
    report_date = stats.get("last_report_date", str(date.today()))
    last_check = stats.get("last_check_datetime", "N/A")

    # Собираем отчет по частям для лучшей читаемости
    report_parts = [
        settings.t("daily_report_title", date=report_date),
        settings.t("daily_report_status_ok"),
        settings.t("daily_report_checks", checks=stats.get("checks_today", 0)),
        settings.t("daily_report_incidents", problems=stats.get("problems_today", 0)),
        settings.t("daily_report_last_check", last_check=last_check),
    ]

    if problematic_members:
        report_parts.append(settings.t("daily_report_problematic_members_header"))
        for member in problematic_members:
            report_parts.append(
                settings.t(
                    "daily_report_problematic_member_line",
                    name=member.name,
                    count=member.problems_count,
                )
            )
    return "".join(report_parts)


def send_daily_report(stats: dict, problematic_members: list[ProblematicMember]):
    """Отправляет ежедневный отчет о работе скрипта и статистике."""
    message = _build_daily_report_message(stats, problematic_members)
    print(f"\n{settings.t('sending_daily_report')}")
    print(message)
    send_telegram_alert(message)


def send_startup_notification():
    """Отправляет уведомление о запуске скрипта."""
    message = settings.t("startup_notification", version=settings.PROJECT_VERSION)
    print("\n" + message)
    send_telegram_alert(message)
