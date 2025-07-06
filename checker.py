"""
Модуль, содержащий бизнес-логику для проверки состояния участников сети ZeroTier.
"""

import platform
import subprocess
import settings
import database_manager as db
from utils import get_seconds_since


def ping_host(ip_address: str) -> bool:
    """
    Проверяет доступность хоста по IP-адресу с помощью одной ICMP-заявки (ping).
    Скрывает вывод команды ping.

    Args:
        ip_address: IP-адрес для проверки.

    Returns:
        True, если хост отвечает на пинг, иначе False.
    """
    # Определяем параметр для количества пингов в зависимости от ОС
    param = "-n" if platform.system().lower() == "windows" else "-c"

    # Формируем команду для выполнения
    command = ["ping", param, "1", ip_address]

    try:
        # Выполняем команду, скрывая ее вывод, и проверяем код возврата.
        # Код 0 обычно означает, что пинг прошел успешно.
        return (
            subprocess.run(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            ).returncode
            == 0
        )
    except FileNotFoundError:
        # Это может произойти, если утилита 'ping' не найдена в системном PATH.
        print(
            f"ОШИБКА: Команда 'ping' не найдена. Невозможно проверить хост {ip_address}."
        )
        return False


def check_member_version(
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


def check_member_online_status(
    name: str,
    last_online_ts: int | None,
    time_ms: int,
    previous_state: dict,
    ip_assignments: list[str],
) -> tuple[str | None, int, int, str]:
    """Проверяет онлайн-статус участника, обрабатывает аномалии и формирует отчет."""
    report = None
    previous_alert_level = previous_state.get("offline_alert_level", 0)
    previous_last_seen_seconds_ago = previous_state.get("last_seen_seconds_ago", -1)

    new_offline_alert_level = previous_alert_level
    seconds_ago = -1
    last_online_str = "N/A"

    if not last_online_ts:
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

                # --- Дополнительная проверка пингом ---
                if ip_assignments:
                    ip_to_ping = ip_assignments[0]
                    print(
                        f"АНАЛИЗ: Узел {name} офлайн. Проверяю пинг до {ip_to_ping}..."
                    )
                    ping_ok = ping_host(ip_to_ping)
                    if ping_ok:
                        report += f"\n  (💡 Пинг до {ip_to_ping} проходит. Возможен сбой контроллера.)"
                    else:
                        report += f"\n  (❗️ Пинг до {ip_to_ping} не проходит. Узел недоступен.)"
                else:
                    print(f"АНАЛИЗ: У узла {name} нет IP-адреса для проверки пинга.")

                new_offline_alert_level = new_alert_level

    return report, new_offline_alert_level, seconds_ago, last_online_str


def process_member(member: dict, latest_version: str, time_ms: int) -> list[str]:
    """
    Обрабатывает одного участника: проверяет состояние, сравнивает с предыдущим,
    сохраняет результат в БД и возвращает отчеты о проблемах.
    """
    node_id = member["nodeId"]
    name = member.get("name", node_id)
    problem_reports = []

    db_row = db.get_member_state(node_id)
    previous_state = dict(db_row) if db_row else {}
    was_version_alert_sent = previous_state.get("version_alert_sent", False)
    new_problems_count = previous_state.get("problems_count", 0)

    client_version = member.get("clientVersion", "N/A").lstrip("v")
    version_report, new_version_alert_sent = check_member_version(
        name, client_version, latest_version, was_version_alert_sent
    )
    if version_report:
        problem_reports.append(version_report)
        new_problems_count += 1

    last_online_ts = member.get("lastSeen")
    # Получаем IP-адреса для возможной проверки пингом
    ip_assignments = member.get("config", {}).get("ipAssignments", [])

    online_report, new_offline_alert_level, seconds_ago, last_online_str = (
        check_member_online_status(
            name, last_online_ts, time_ms, previous_state, ip_assignments
        )
    )
    if online_report:
        problem_reports.append(online_report)
        if "снова в сети" not in online_report:
            new_problems_count += 1

    version_status = "OK" if client_version == latest_version else "OLD"
    print(
        f"ID: {node_id}, Имя: {name}, Версия: {client_version or 'N/A'} [{version_status}], Онлайн: {last_online_str}"
    )

    db.update_member_state(
        node_id,
        name,
        new_version_alert_sent,
        new_offline_alert_level,
        seconds_ago,
        new_problems_count,
    )

    return problem_reports
