"""Модуль для мониторинга состояния устройств в сетях ZeroTier."""

import time
from datetime import date, datetime
from send_to_chat import (
    report_findings,
    send_daily_report,
    send_startup_notification,
)
from utils import now_datetime
import settings
import api_client
import database_manager as db  # Используем новый модуль для работы с БД
import checker


def run_check_cycle(statistics: dict) -> None:
    """Основной цикл проверки состояния участников ZeroTier."""
    check_time_str = now_datetime()
    print(settings.t("current_datetime", check_time_str=check_time_str))

    statistics["checks_today"] += 1
    # Сохраняем точное время последней проверки
    statistics["last_check_datetime"] = check_time_str
    time_ms = int(datetime.now().timestamp() * 1000)

    latest_version = api_client.get_latest_zerotier_version()
    print(settings.t("latest_zt_version", latest_version=latest_version))

    all_members = api_client.get_all_members(settings.ZEROTIER_NETWORKS)

    if not all_members:
        print(settings.t("get_members_failed_skipping"))
        return

    print("\n--- Результаты проверки ---")

    all_problem_reports = []
    monitored_members = [m for m in all_members if m["nodeId"] in settings.MEMBER_IDS]

    for member in monitored_members:
        member_reports = checker.process_member(member, latest_version, time_ms)
        all_problem_reports.extend(member_reports)

    if all_problem_reports:
        report_findings(all_problem_reports, statistics)
    else:
        print(f"\n{settings.t('no_new_problems')}")


def start_monitoring():
    """Инициализирует и запускает бесконечный цикл мониторинга."""
    # Инициализируем базу данных при первом запуске
    db.initialize_database()

    send_startup_notification()

    # Загрузка статистики из БД
    stats = db.get_stats()
    # Безопасно получаем и проверяем дату последнего отчета
    try:
        last_report_date_str = stats.get("last_report_date")
        if not last_report_date_str:
            raise ValueError("Last report date is missing or empty.")
        last_report_date = date.fromisoformat(last_report_date_str)
    except (ValueError, TypeError):
        # Если дата некорректна, отсутствует или неверного формата,
        # устанавливаем текущую дату и обновляем ее в словаре, не сбрасывая другие счетчики.
        print(settings.t("invalid_report_date_in_db"))
        last_report_date = date.today()
        stats["last_report_date"] = str(last_report_date)

    while True:
        current_date = date.today()

        # Проверяем, наступил ли новый день
        if current_date > last_report_date:
            print(
                f"\n{settings.t('new_day_started', current_date=current_date, last_report_date=last_report_date)}"
            )
            problematic_members = db.get_problematic_members()
            send_daily_report(stats, problematic_members)

            # Сброс статистики для нового дня
            last_report_date = current_date
            stats["last_report_date"] = str(current_date)
            stats["checks_today"] = 0
            stats["problems_today"] = 0
            db.reset_daily_problem_counts()

        try:
            run_check_cycle(stats)
        except ValueError as e:
            # Логируем непредвиденную ошибку, чтобы скрипт не падал
            print(f"\n{settings.t('unexpected_error', e=e)}")

        # Сохраняем обновленную статистику в БД после каждой проверки
        db.save_stats(stats)
        print(
            f"\n{settings.t('pause_before_next_check', minutes=settings.CHECK_INTERVAL_SECONDS // 60)}"
        )
        time.sleep(settings.CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    start_monitoring()
