"""
Модуль, содержащий бизнес-логику для проверки состояния участников сети ZeroTier.
"""

import platform
import subprocess
import settings
from utils import get_seconds_since
from models import MemberState, OnlineStatusResult


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
        print(settings.t("ping_command_not_found", ip=ip_address))
        return False


def check_member_version(
    name: str,
    client_version: str,
    latest_version: str,
    was_version_alert_sent: bool,
) -> tuple[str | None, bool]:
    """Проверяет версию клиента ZeroTier и формирует отчет при необходимости.

    Args:
        name: Имя участника сети.
        client_version: Текущая версия клиента ZeroTier на устройстве.
        latest_version: Последняя актуальная версия ZeroTier.
        was_version_alert_sent: Флаг, указывающий, было ли уже отправлено
                                уведомление о старой версии.

    Returns:
        Кортеж, содержащий (отчет о версии или None, новый статус флага уведомления).
    """
    is_version_ok = client_version == latest_version
    report = None
    new_version_alert_sent = was_version_alert_sent

    if not is_version_ok and client_version != "N/A":
        if not was_version_alert_sent:
            report = settings.t("version_report_old", name=name, version=client_version)
            new_version_alert_sent = True
    elif was_version_alert_sent and is_version_ok:
        report = settings.t("version_report_updated", name=name, version=client_version)
        new_version_alert_sent = False

    return report, new_version_alert_sent


def check_member_online_status(
    name: str,
    last_online_ts: int | None,
    time_ms: int,
    previous_state: MemberState | None,
    ip_assignments: list[str],
) -> OnlineStatusResult:
    """Проверяет онлайн-статус участника, обрабатывает аномалии и формирует отчет."""
    report = None
    previous_alert_level = previous_state.offline_alert_level if previous_state else 0
    previous_last_seen_seconds_ago = (
        previous_state.last_seen_seconds_ago if previous_state else -1
    )

    new_offline_alert_level = previous_alert_level
    seconds_ago = -1
    last_online_str = "N/A"

    if not last_online_ts:
        if previous_state is None:
            report = settings.t("member_never_online", name=name)
        return OnlineStatusResult(
            report, new_offline_alert_level, seconds_ago, last_online_str
        )

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
            settings.t(
                "anomaly_detected",
                name=name,
                api_s=api_seconds_ago,
                prev_s=previous_last_seen_seconds_ago,
                calc_s=seconds_ago,
            )
        )
        last_online_str = settings.t("last_seen_calculated", seconds=seconds_ago)
    else:
        last_online_str = settings.t("last_seen_normal", seconds=seconds_ago)

    if seconds_ago <= settings.ONLINE_THRESHOLD_SECONDS:
        if previous_alert_level > 0:
            print(settings.t("device_back_online", name=name))
            report = settings.t("member_back_online_report", name=name)
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
                message_key = settings.OFFLINE_THRESHOLDS[triggered_level_key][
                    "message_key"
                ]
                report = settings.t(message_key, name=name)

                # --- Дополнительная проверка пингом ---
                if ip_assignments:
                    ip_to_ping = ip_assignments[0]
                    print(
                        settings.t(
                            "checking_ping_for_offline_node", name=name, ip=ip_to_ping
                        )
                    )
                    ping_ok = ping_host(ip_to_ping)
                    if ping_ok:
                        report += settings.t("ping_success_report", ip=ip_to_ping)
                    else:
                        report += settings.t("ping_fail_report", ip=ip_to_ping)
                else:
                    print(settings.t("no_ip_for_ping", name=name))

                new_offline_alert_level = new_alert_level

    return OnlineStatusResult(
        report, new_offline_alert_level, seconds_ago, last_online_str
    )


def process_member(
    member: dict,
    latest_version: str,
    time_ms: int,
    previous_state: MemberState | None,
) -> tuple[MemberState, list[str]]:
    """
    Обрабатывает одного участника: проверяет состояние, сравнивает с предыдущим,
    и возвращает новое состояние и отчеты о проблемах.
    """
    node_id = member["nodeId"]
    name = member.get("name", node_id)
    problem_reports = []

    # Используем предыдущее состояние или создаем новое, если участник не найден в БД
    current_state = previous_state or MemberState(node_id=node_id, name=name)
    new_problems_count = current_state.problems_count

    client_version = member.get("clientVersion", "N/A").lstrip("v")
    version_report, new_version_alert_sent = check_member_version(
        name, client_version, latest_version, current_state.version_alert_sent
    )
    if version_report:
        problem_reports.append(version_report)
        new_problems_count += 1

    last_online_ts = member.get("lastSeen")
    # Получаем IP-адреса для возможной проверки пингом
    ip_assignments = member.get("config", {}).get("ipAssignments", [])

    online_status = check_member_online_status(
        name, last_online_ts, time_ms, current_state, ip_assignments
    )

    if online_status.report:
        problem_reports.append(online_status.report)
        # Не считаем проблемой, если узел просто вернулся в онлайн
        if online_status.report != settings.t("member_back_online_report", name=name):
            new_problems_count += 1

    version_status = "OK" if client_version == latest_version else "OLD"
    print(
        settings.t(
            "check_result_log",
            id=node_id,
            name=name,
            version=(client_version or "N/A"),
            status=version_status,
            online_str=online_status.last_online_str,
        )
    )

    # Создаем и сохраняем новое состояние
    new_state = MemberState(
        node_id,
        name,
        new_version_alert_sent,
        online_status.new_offline_alert_level,
        online_status.seconds_ago,
        new_problems_count,
    )

    return new_state, problem_reports
