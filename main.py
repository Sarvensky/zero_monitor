"""Модуль для мониторинга состояния устройств в сетях ZeroTier."""

import time
from datetime import date, datetime

import api_client
import checker
import database_manager as db
import settings
from send_to_chat import (
    report_findings,
    send_daily_report,
    send_startup_notification,
    send_exit_notification,
)
from utils import now_datetime


class AppStateManager:
    """
    Класс для управления состоянием и статистикой приложения.
    Инкапсулирует логику загрузки, сохранения и обновления статистики.
    """

    last_report_date: date

    def __init__(self):
        """Инициализирует менеджер состояния, загружая статистику из БД."""
        self.stats: dict = db.get_stats()
        self.last_report_date = self._load_last_report_date()

    def _load_last_report_date(self) -> date:
        """Безопасно загружает и валидирует дату последнего отчета."""
        try:
            last_report_date_str = self.stats.get("last_report_date")
            if not last_report_date_str:
                raise ValueError("Last report date is missing or empty.")
            return date.fromisoformat(last_report_date_str)
        except (ValueError, TypeError):
            print(settings.t("invalid_report_date_in_db"))
            # Если дата некорректна, устанавливаем текущую и сохраняем в статистику.
            today = date.today()
            self.stats["last_report_date"] = str(today)
            return today

    def save(self):
        """Сохраняет текущую статистику в базу данных."""
        db.save_stats(self.stats)

    def handle_daily_rollover(self):
        """
        Проверяет, наступил ли новый день. Если да, отправляет
        ежедневный отчет и сбрасывает суточные счетчики.
        """
        current_date = date.today()
        if current_date > self.last_report_date:
            print(
                f"\n{settings.t('new_day_started', current_date=current_date, last_report_date=self.last_report_date)}"
            )
            problematic_members = db.get_problematic_members()
            send_daily_report(self.stats, problematic_members)

            # Сброс статистики для нового дня
            self.last_report_date = current_date
            self.stats["last_report_date"] = str(current_date)
            self.stats["checks_today"] = 0
            self.stats["problems_today"] = 0
            db.reset_daily_problem_counts()

    def increment_checks(self):
        """Увеличивает счетчик проверок за день."""
        self.stats["checks_today"] += 1

    def add_problem_reports(self, reports: list[str]):
        """Добавляет количество новых проблем к суточному счетчику."""
        self.stats["problems_today"] += len(reports)

    def update_last_check_time(self):
        """Обновляет время последней успешной проверки."""
        self.stats["last_check_datetime"] = now_datetime()


def run_check_cycle(state: AppStateManager) -> None:
    """Основной цикл проверки состояния участников ZeroTier."""
    state.update_last_check_time()
    state.increment_checks()
    print(
        settings.t(
            "current_datetime", check_time_str=state.stats["last_check_datetime"]
        )
    )

    time_ms = int(datetime.now().timestamp() * 1000)

    latest_version = api_client.get_latest_zerotier_version()
    print(settings.t("latest_zt_version", latest_version=latest_version))

    all_members = api_client.get_all_members(settings.ZEROTIER_NETWORKS)

    if not all_members:
        print(settings.t("get_members_failed_skipping"))
        return

    print(f"\n{settings.t('check_results_header')}")

    all_problem_reports = []
    monitored_members = [m for m in all_members if m["nodeId"] in settings.MEMBER_IDS]

    for member in monitored_members:
        node_id = member["nodeId"]
        # 1. Получаем предыдущее состояние из БД
        previous_state = db.get_member_state(node_id)
        # 2. Вызываем "чистую" функцию проверки, передавая ей состояние
        new_state, member_reports = checker.process_member(
            member, latest_version, time_ms, previous_state
        )
        # 3. Сохраняем новое состояние в БД
        db.update_member_state(new_state)
        all_problem_reports.extend(member_reports)

    if all_problem_reports:
        state.add_problem_reports(all_problem_reports)
        report_findings(all_problem_reports)
    else:
        print(f"\n{settings.t('no_new_problems')}")


def start_monitoring():
    """Инициализирует и запускает бесконечный цикл мониторинга."""
    db.initialize_database()
    send_startup_notification()

    state = AppStateManager()

    while True:
        try:
            state.handle_daily_rollover()
            run_check_cycle(state)

            # Сохраняем обновленную статистику в БД после каждой проверки
            state.save()
            print(
                f"\n{settings.t('pause_before_next_check', minutes=settings.CHECK_INTERVAL_SECONDS // 60)}"
            )
            time.sleep(settings.CHECK_INTERVAL_SECONDS)
        except KeyboardInterrupt:
            send_exit_notification()
            print(settings.t("script_stopped_by_user"))
            break
        # pylint: disable=broad-exception-caught
        except Exception as e:
            # Логируем непредвиденную ошибку, чтобы скрипт не падал
            print(f"\n{settings.t('unexpected_error', e=e)}")
            # Добавляем паузу после ошибки, чтобы избежать "горячего" цикла
            # в случае повторяющейся проблемы.
            time.sleep(settings.CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    start_monitoring()
