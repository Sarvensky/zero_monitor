"""Модуль для мониторинга состояния устройств в сетях ZeroTier."""

import time
from datetime import date, datetime
from send_to_chat import (
    report_findings,
    send_daily_report,
    send_startup_notification,
)
import settings
import api_client
import database_manager as db  # Используем новый модуль для работы с БД
from utils import get_seconds_since, now_datetime


def _check_member_version(
    name: str,
    client_version: str,
    latest_version: str,
    was_version_alert_sent: bool,
) -> tuple[str | None, bool]:
    """Проверяет версию клиента и формирует отчет при необходимости."""
    is_version_ok = client_version == latest_version
    report = None
    new_version_alert_sent = was_version_alert_sent

    if not is_version_ok and client_version != "N/A":
        if not was_version_alert_sent:
            report = f"🔧 {name}: старая версия ({client_version})"
            new_version_alert_sent = True
    elif was_version_alert_sent and is_version_ok:
        report = f"✅ {name}: версия обновлена до актуальной ({client_version})"
        new_version_alert_sent = False

    return report, new_version_alert_sent


def _check_member_online_status(
    name: str,
    last_online_ts: int | None,
    time_ms: int,
    previous_state: dict,
) -> tuple[str | None, int, int, str]:
    """Проверяет онлайн-статус участника, обрабатывает аномалии и формирует отчет."""
    report = None
    previous_alert_level = previous_state.get("offline_alert_level", 0)
    previous_last_seen_seconds_ago = previous_state.get("last_seen_seconds_ago", -1)

    new_offline_alert_level = previous_alert_level
    seconds_ago = -1
    last_online_str = "N/A"

    if not last_online_ts:
        # Если узел никогда не был в сети и его еще нет в БД, создаем отчет
        if not previous_state:
            report = f"❓ {name}: ни разу не был в сети."
        return report, new_offline_alert_level, seconds_ago, last_online_str

    api_seconds_ago = get_seconds_since(last_online_ts, time_ms)
    seconds_ago = api_seconds_ago

    anomaly_jump_threshold = (
        previous_last_seen_seconds_ago
        + settings.CHECK_INTERVAL_SECONDS
        + settings.LAST_SEEN_ANOMALY_THRESHOLD_SECONDS
    )

    if (
        previous_last_seen_seconds_ago != -1
        and api_seconds_ago > anomaly_jump_threshold
    ):
        seconds_ago = previous_last_seen_seconds_ago + settings.CHECK_INTERVAL_SECONDS
        print(
            f"АНАЛИЗ: Обнаружен аномальный скачок 'lastSeen' для {name}. "
            f"API: {api_seconds_ago} сек, Предыдущее: {previous_last_seen_seconds_ago} сек. "
            f"Используется расчетное значение: {seconds_ago} сек."
        )
        last_online_str = f"~{seconds_ago} сек. назад (расчетное)"
    else:
        last_online_str = f"{seconds_ago} сек. назад"

    if seconds_ago <= settings.ONLINE_THRESHOLD_SECONDS:
        if previous_alert_level > 0:
            print(f"✅ Устройство {name} снова в сети.")
            report = f"✅ {name}: снова в сети."
            new_offline_alert_level = 0
    else:
        triggered_level_key = None
        sorted_thresholds = sorted(
            settings.OFFLINE_THRESHOLDS.items(),
            key=lambda item: item[1]["level"],
            reverse=True,
        )
        for key, data in sorted_thresholds:
            if seconds_ago > data["seconds"]:
                triggered_level_key = key
                break

        if triggered_level_key:
            new_alert_level = settings.OFFLINE_THRESHOLDS[triggered_level_key]["level"]
            if new_alert_level > previous_alert_level:
                report = settings.OFFLINE_THRESHOLDS[triggered_level_key][
                    "message"
                ].format(name=name)
                new_offline_alert_level = new_alert_level

    return report, new_offline_alert_level, seconds_ago, last_online_str


def _process_member(member: dict, latest_version: str, time_ms: int) -> list[str]:
    """
    Обрабатывает одного участника: проверяет состояние, сравнивает с предыдущим,
    сохраняет результат в БД и возвращает отчеты о проблемах.
    """
    node_id = member["nodeId"]
    name = member.get("name", node_id)
    problem_reports = []

    # 1. Получаем предыдущее состояние из БД (или пустой словарь, если нет)
    # Конвертируем sqlite3.Row в dict, чтобы избежать ошибок с .get() и типизацией
    db_row = db.get_member_state(node_id)
    previous_state = dict(db_row) if db_row else {}
    was_version_alert_sent = previous_state.get("version_alert_sent", False)
    new_problems_count = previous_state.get("problems_count", 0)

    # 2. Проверка версии
    client_version = member.get("clientVersion", "N/A").lstrip("v")
    version_report, new_version_alert_sent = _check_member_version(
        name, client_version, latest_version, was_version_alert_sent
    )
    if version_report:
        problem_reports.append(version_report)
        new_problems_count += 1

    # 3. Проверка онлайн-статуса
    last_online_ts = member.get("lastSeen")
    online_report, new_offline_alert_level, seconds_ago, last_online_str = (
        _check_member_online_status(name, last_online_ts, time_ms, previous_state)
    )
    if online_report:
        problem_reports.append(online_report)
        # Не считаем "снова в сети" за новую проблему
        if "снова в сети" not in online_report:
            new_problems_count += 1

    # 4. Вывод статуса в консоль
    version_status = "OK" if client_version == latest_version else "OLD"
    print(
        f"ID: {node_id}, Имя: {name}, Версия: {client_version or 'N/A'} [{version_status}], Онлайн: {last_online_str}"
    )

    # 5. Сохраняем итоговое новое состояние в БД
    db.update_member_state(
        node_id,
        name,
        new_version_alert_sent,
        new_offline_alert_level,
        seconds_ago,
        new_problems_count,
    )

    return problem_reports


def run_check_cycle(statistics: dict) -> None:
    """Основной цикл проверки состояния участников ZeroTier."""
    check_time_str = now_datetime()
    print(f"Дата и время сейчас: {check_time_str}")

    statistics["checks_today"] += 1
    # Сохраняем точное время последней проверки
    statistics["last_check_datetime"] = check_time_str
    time_ms = int(datetime.now().timestamp() * 1000)

    latest_version = api_client.get_latest_zerotier_version()
    print(f"Актуальная версия ZeroTier: {latest_version}")

    all_members = api_client.get_all_members(settings.ZEROTIER_NETWORKS)

    if not all_members:
        print("Не удалось получить информацию об участниках сети. Пропуск проверки.")
        return

    print("\n--- Результаты проверки ---")

    all_problem_reports = []
    monitored_members = [m for m in all_members if m["nodeId"] in settings.MEMBER_IDS]

    for member in monitored_members:
        member_reports = _process_member(member, latest_version, time_ms)
        all_problem_reports.extend(member_reports)

    if all_problem_reports:
        report_findings(all_problem_reports, statistics)
    else:
        print("\nНовых проблем или изменений статуса не обнаружено.")


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
            # Это условие сработает, если ключ отсутствует или значение None/пустая строка
            raise ValueError("Дата последнего отчета отсутствует или пуста.")
        last_report_date = date.fromisoformat(last_report_date_str)
    except (ValueError, TypeError):
        # Если дата некорректна, отсутствует или неверного формата,
        # устанавливаем текущую дату и обновляем ее в словаре, не сбрасывая другие счетчики.
        print("Некорректная дата последнего отчета в БД. Используется текущая дата.")
        last_report_date = date.today()
        stats["last_report_date"] = str(last_report_date)

    while True:
        current_date = date.today()

        # Проверяем, наступил ли новый день (полночь)
        if current_date > last_report_date:
            print(
                f"\n--- Наступил новый день ({current_date}). Отправка отчета за {last_report_date}. ---"
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
            print(f"\n--- Произошла непредвиденная ошибка: {e} ---")

        # Сохраняем обновленную статистику в БД после каждой проверки
        db.save_stats(stats)
        print(
            f"\n--- Пауза {settings.CHECK_INTERVAL_SECONDS // 60} минут до следующей проверки ---"
        )
        time.sleep(settings.CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    start_monitoring()
