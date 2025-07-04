"""Модуль для мониторинга состояния устройств в сетях ZeroTier."""

import time
import json
from datetime import datetime, date
from send_to_chat import (
    report_findings,
    send_daily_report,
    send_startup_notification,
)
import settings  # Импортируем модуль с настройками
import api_client  # Импортируем новый модуль для работы с API
import file_manager  # Импортируем модуль для работы с файлами


def now_datetime():
    """Возвращает текущую дату и время в отформатированной строке."""
    return datetime.now().strftime("Дата и время сейчас: %Y-%m-%d %H:%M:%S")


def get_seconds_since(last_online, time_ms):
    """
    Вычисляет разницу в секундах между текущим временем (time_ms)
    и временем последнего онлайна (last_online).
    Оба значения должны быть в миллисекундах.
    Возвращает целое число секунд.
    """
    diff_seconds = abs(time_ms - last_online) / 1000
    return int(diff_seconds)


def check_member_status(member, latest_version, time_ms, offline_threshold_sec=300):
    """
    Проверяет статус участника (устаревшая версия, офлайн) и возвращает
    отформатированную строку с информацией и список обнаруженных проблем.
    """
    node_id = member["nodeId"]
    name = member.get("name", "N/A")
    problems = []

    # Проверка версии
    client_version = member.get("clientVersion", "N/A").lstrip("v")
    is_version_ok = client_version == latest_version
    version_status = "OK" if is_version_ok else "OLD"
    if not is_version_ok and client_version != "N/A":
        problems.append(f"старая версия ({client_version})")

    # Проверка времени последнего онлайна
    last_online_ts = member.get("lastSeen")
    if last_online_ts:
        seconds_ago = get_seconds_since(last_online_ts, time_ms)
        last_online_str = f"{seconds_ago} сек. назад"
        if seconds_ago > offline_threshold_sec:
            if offline_threshold_sec >= 3600:
                hours = offline_threshold_sec // 3600
                problems.append(f"офлайн более {hours} ч")
            else:
                minutes = offline_threshold_sec // 60
                problems.append(f"офлайн более {minutes} мин")
    else:
        last_online_str = "N/A"
        problems.append("не был онлайн")

    info_string = (
        f"ID: {node_id}, Имя: {name}, "
        f"Версия: {client_version or 'N/A'} [{version_status}], "
        f"Онлайн: {last_online_str}"
    )

    return info_string, problems


def main(statistics: dict):
    """Основная функция для запуска мониторинга ZeroTier."""
    print(now_datetime())

    statistics["checks_today"] += 1
    time_ms = int(datetime.now().timestamp() * 1000)

    # Загружаем предыдущее состояние оповещений
    # Выполняем глубокое копирование, чтобы безопасно изменять вложенные словари
    alert_state = file_manager.load_state(settings.STATE_FILE)
    new_alert_state = json.loads(json.dumps(alert_state))

    latest_version = api_client.get_latest_zerotier_version()
    print(f"Актуальная версия ZeroTier: {latest_version}")

    all_members = api_client.get_all_members(settings.ZEROTIER_NETWORKS)

    if not all_members:
        print("Не удалось получить информацию об участниках сети. Завершение работы.")
        return

    print("\n--- Результаты проверки ---")

    problem_reports = []

    # Фильтруем и обрабатываем только отслеживаемых участников
    monitored_members = [m for m in all_members if m["nodeId"] in settings.MEMBER_IDS]

    for member in monitored_members:
        node_id = member["nodeId"]
        name = member.get("name", node_id)

        # Получаем предыдущее состояние для конкретного устройства
        previous_node_state = alert_state.get(node_id, {})

        # --- 1. Проверка версии (с сохранением состояния) ---
        client_version = member.get("clientVersion", "N/A").lstrip("v")
        is_version_ok = client_version == latest_version
        version_status = "OK" if is_version_ok else "OLD"
        was_version_alert_sent = previous_node_state.get("version_alert_sent", False)

        if not is_version_ok and client_version != "N/A":
            # Если версия старая и оповещение еще не отправлялось
            if not was_version_alert_sent:
                problem_reports.append(f"🔧 {name}: старая версия ({client_version})")
                new_alert_state.setdefault(node_id, {})["version_alert_sent"] = True
        elif was_version_alert_sent:
            # Если версия теперь в порядке, а раньше было оповещение
            problem_reports.append(
                f"✅ {name}: версия обновлена до актуальной ({client_version})."
            )
            if (
                node_id in new_alert_state
                and "version_alert_sent" in new_alert_state[node_id]
            ):
                del new_alert_state[node_id]["version_alert_sent"]

        # --- 2. Проверка онлайн-статуса (с сохранением состояния) ---
        last_online_ts = member.get("lastSeen")
        last_online_str = "N/A"
        previous_alert_level = previous_node_state.get("level", 0)

        if last_online_ts:
            seconds_ago = get_seconds_since(last_online_ts, time_ms)
            last_online_str = f"{seconds_ago} сек. назад"

            # Устройство снова в сети
            if seconds_ago <= settings.ONLINE_THRESHOLD_SECONDS:
                if previous_alert_level > 0:  # Было оповещение об офлайне
                    print(f"✅ Устройство {name} ({node_id}) снова в сети.")
                    problem_reports.append(f"✅ {name}: снова в сети.")
                    if (
                        node_id in new_alert_state
                        and "level" in new_alert_state[node_id]
                    ):
                        del new_alert_state[node_id]["level"]
            # Устройство оффлайн
            else:
                triggered_level_key = None
                # Ищем самый высокий уровень тревоги, который был превышен
                # Сортируем по уровню, от большего к меньшему, для корректной логики
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
                    # Отправляем уведомление только если уровень тревоги повысился
                    if new_alert_level > previous_alert_level:
                        message = settings.OFFLINE_THRESHOLDS[triggered_level_key][
                            "message"
                        ].format(name=name)
                        problem_reports.append(message)
                        new_alert_state.setdefault(node_id, {})[
                            "level"
                        ] = new_alert_level
        else:  # Устройство ни разу не было в сети
            last_online_str = "N/A"
            if node_id not in alert_state:  # Отправляем только один раз
                problem_reports.append(f"❓ {name}: ни разу не был в сети.")
                new_alert_state.setdefault(node_id, {})["level"] = 0

        print(
            f"ID: {node_id}, Имя: {name}, Версия: {client_version or 'N/A'} [{version_status}], Онлайн: {last_online_str}"
        )

    if problem_reports:
        report_findings(problem_reports, statistics)
    else:
        print("\nНовых проблем или изменений статуса не обнаружено.")

    # Очищаем состояние для устройств, у которых больше нет проблем
    final_alert_state = {
        node_id: state for node_id, state in new_alert_state.items() if state
    }

    # Сохраняем обновленное состояние для следующего запуска
    file_manager.save_state(settings.STATE_FILE, final_alert_state)


if __name__ == "__main__":
    # Отправляем уведомление о запуске
    send_startup_notification()

    # Загрузка и инициализация статистики
    stats = file_manager.load_stats(settings.STATS_FILE)
    try:
        # Преобразуем строку с датой в объект date для корректного сравнения
        last_report_date = date.fromisoformat(stats["last_report_date"])
    except (ValueError, TypeError, KeyError):
        # Если дата некорректна или отсутствует, инициализируем с сегодняшней датой
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

        # Сохраняем обновленную статистику в файл после каждой проверки
        file_manager.save_stats(settings.STATS_FILE, stats)
        print(
            f"\n--- Пауза {settings.CHECK_INTERVAL_SECONDS // 60} минут до следующей проверки ---"
        )
        time.sleep(settings.CHECK_INTERVAL_SECONDS)
