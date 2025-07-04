"""Модуль для мониторинга состояния устройств в сетях ZeroTier."""

import time
from datetime import datetime, date
from send_to_chat import (
    report_findings,
    send_daily_report,
    send_startup_notification,
)
import settings
import api_client
import database_manager as db  # Используем новый модуль для работы с БД


def now_datetime() -> str:
    """Возвращает текущую дату и время в отформатированной строке."""
    return datetime.now().strftime("Дата и время сейчас: %Y-%m-%d %H:%M:%S")


def get_seconds_since(last_online, time_ms) -> int:
    """
    Вычисляет разницу в секундах между текущим временем (time_ms)
    и временем последнего онлайна (last_online).
    Оба значения должны быть в миллисекундах.
    Возвращает целое число секунд.
    """
    diff_seconds = abs(time_ms - last_online) / 1000
    return int(diff_seconds)


def main(statistics: dict) -> None:
    """Основная функция для запуска мониторинга ZeroTier."""
    print(now_datetime())

    statistics["checks_today"] += 1
    time_ms = int(datetime.now().timestamp() * 1000)

    latest_version = api_client.get_latest_zerotier_version()
    print(f"Актуальная версия ZeroTier: {latest_version}")

    all_members = api_client.get_all_members(settings.ZEROTIER_NETWORKS)

    if not all_members:
        print("Не удалось получить информацию об участниках сети. Пропуск проверки.")
        return

    print("\n--- Результаты проверки ---")

    problem_reports = []

    monitored_members = [m for m in all_members if m["nodeId"] in settings.MEMBER_IDS]

    for member in monitored_members:
        node_id = member["nodeId"]
        name = member.get("name", node_id)

        # 1. Получаем предыдущее состояние из БД
        previous_state = db.get_member_state(node_id)
        was_version_alert_sent = (
            previous_state["version_alert_sent"] if previous_state else False
        )
        previous_alert_level = (
            previous_state["offline_alert_level"] if previous_state else 0
        )

        # 2. Инициализируем новое состояние на основе предыдущего
        new_version_alert_sent = was_version_alert_sent
        new_offline_alert_level = previous_alert_level

        # --- 3. Проверка версии ---
        client_version = member.get("clientVersion", "N/A").lstrip("v")
        is_version_ok = client_version == latest_version
        version_status = "OK" if is_version_ok else "OLD"

        if not is_version_ok and client_version != "N/A":
            if not was_version_alert_sent:
                problem_reports.append(f"🔧 {name}: старая версия ({client_version})")
                new_version_alert_sent = True
        elif was_version_alert_sent:
            problem_reports.append(
                f"✅ {name}: версия обновлена до актуальной ({client_version})."
            )
            new_version_alert_sent = False

        # --- 4. Проверка онлайн-статуса ---
        last_online_ts = member.get("lastSeen")
        last_online_str = "N/A"

        if last_online_ts:
            seconds_ago = get_seconds_since(last_online_ts, time_ms)
            last_online_str = f"{seconds_ago} сек. назад"

            if seconds_ago <= settings.ONLINE_THRESHOLD_SECONDS:
                if previous_alert_level > 0:
                    print(f"✅ Устройство {name} ({node_id}) снова в сети.")
                    problem_reports.append(f"✅ {name}: снова в сети.")
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
                    new_alert_level = settings.OFFLINE_THRESHOLDS[triggered_level_key][
                        "level"
                    ]
                    if new_alert_level > previous_alert_level:
                        message = settings.OFFLINE_THRESHOLDS[triggered_level_key][
                            "message"
                        ].format(name=name)
                        problem_reports.append(message)
                        new_offline_alert_level = new_alert_level
        else:
            last_online_str = "N/A"
            if (
                not previous_state
            ):  # Отправляем только один раз, если устройства нет в БД
                problem_reports.append(f"❓ {name}: ни разу не был в сети.")

        print(
            f"ID: {node_id}, Имя: {name}, Версия: {client_version or 'N/A'} [{version_status}], Онлайн: {last_online_str}"
        )

        # 5. Сохраняем итоговое новое состояние в БД для этого участника
        db.update_member_state(
            node_id, name, new_version_alert_sent, new_offline_alert_level
        )

    if problem_reports:
        report_findings(problem_reports, statistics)
    else:
        print("\nНовых проблем или изменений статуса не обнаружено.")


if __name__ == "__main__":
    # Инициализируем базу данных при первом запуске
    db.initialize_database()

    send_startup_notification()

    # Загрузка статистики из БД
    stats = db.get_stats()
    try:
        # Преобразуем строку с датой в объект date для корректного сравнения
        last_report_date = date.fromisoformat(stats["last_report_date"])
    except (ValueError, TypeError, KeyError):
        # Если дата некорректна, отсутствует или неверного формата
        last_report_date = date.today()
        stats = {
            "last_report_date": str(last_report_date),
            "checks_today": 0,
            "problems_today": 0,
        }

    while True:
        current_date = date.today()

        # Проверяем, наступил ли новый день (полночь)
        if current_date > last_report_date:
            print(
                f"\n--- Наступил новый день ({current_date}). Отправка отчета за {last_report_date}. ---"
            )
            send_daily_report(stats)

            # Сброс статистики для нового дня
            last_report_date = current_date
            stats["last_report_date"] = str(current_date)
            stats["checks_today"] = 0
            stats["problems_today"] = 0

        try:
            main(stats)
        except ValueError as e:
            # Логируем непредвиденную ошибку, чтобы скрипт не падал
            print(f"\n--- Произошла непредвиденная ошибка: {e} ---")

        # Сохраняем обновленную статистику в БД после каждой проверки
        db.save_stats(stats)
        print(
            f"\n--- Пауза {settings.CHECK_INTERVAL_SECONDS // 60} минут до следующей проверки ---"
        )
        time.sleep(settings.CHECK_INTERVAL_SECONDS)
