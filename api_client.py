"""
Модуль для взаимодействия с API ZeroTier и получения информации о членах сетей, а также о последней версии ZeroTier.
Содержит функции с поддержкой повторных попыток и уведомлений в случае ошибок.
"""

import time
import requests
import settings
from send_to_chat import send_telegram_alert


def get_members(token: str, network_id: str) -> list | None:
    """Получает список участников для одной сети ZeroTier с несколькими попытками."""
    url = f"{settings.API_URL}network/{network_id}/member"
    headers = {"Authorization": f"Bearer {token}"}
    last_error = None

    for attempt in range(settings.API_RETRY_ATTEMPTS):
        try:
            response = requests.get(url=url, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            last_error = e
            print(
                f"{settings.t('attempt_info', attempt=attempt + 1, total=settings.API_RETRY_ATTEMPTS)} "
                f"{settings.t('error_getting_members', net_id=network_id, e=e)}"
            )
            if attempt < settings.API_RETRY_ATTEMPTS - 1:
                print(
                    settings.t(
                        "retry_in_seconds", delay=settings.API_RETRY_DELAY_SECONDS
                    )
                )
                time.sleep(settings.API_RETRY_DELAY_SECONDS)
            else:
                print(settings.t("all_attempts_failed"))
    # Отправляем уведомление только после того, как все попытки провалились
    if last_error:
        error_message = settings.t(
            "alert_failed_to_get_members",
            net_id=network_id,
            attempts=settings.API_RETRY_ATTEMPTS,
            error=last_error,
        )
        send_telegram_alert(error_message)
    return None


def get_all_members(networks: list[dict]) -> list[dict]:
    """Получает и объединяет участников из всех указанных сетей ZeroTier."""
    print(settings.t("getting_members_info"))
    all_members = []
    num_networks = len(networks)
    for i, network in enumerate(networks):
        members = get_members(network["token"], network["network_id"])
        if members:
            all_members.extend(members)
        else:
            print(
                settings.t(
                    "failed_to_get_members_for_network", net_id=network["network_id"]
                )
            )

        # Добавляем паузу между запросами к разным сетям, чтобы не превышать лимиты API.
        # Пауза не нужна после последнего запроса.
        if i < num_networks - 1:
            time.sleep(1)
    return all_members


def get_latest_zerotier_version() -> str:
    """Получает последнюю версию ZeroTier с GitHub API с несколькими попытками."""
    url = "https://api.github.com/repos/zerotier/ZeroTierOne/releases/latest"
    fallback_version = "1.14.2"  # Версия на случай сбоя API
    last_error = None

    for attempt in range(settings.API_RETRY_ATTEMPTS):
        try:
            response = requests.get(url=url, timeout=10)
            response.raise_for_status()
            data = response.json()
            # Теги на GitHub часто имеют префикс 'v', уберем его
            return data["tag_name"].lstrip("v")
        except (requests.RequestException, KeyError, ValueError) as e:
            last_error = e
            print(
                f"{settings.t('attempt_info', attempt=attempt + 1, total=settings.API_RETRY_ATTEMPTS)} "
                f"{settings.t('error_getting_latest_version', e=e)}"
            )
            if attempt < settings.API_RETRY_ATTEMPTS - 1:
                print(
                    settings.t(
                        "retry_in_seconds", delay=settings.API_RETRY_DELAY_SECONDS
                    )
                )
                time.sleep(settings.API_RETRY_DELAY_SECONDS)
            else:
                print(settings.t("all_attempts_failed"))
    # Отправляем уведомление только после того, как все попытки провалились
    if last_error:
        error_message = settings.t(
            "alert_failed_to_get_latest_version",
            attempts=settings.API_RETRY_ATTEMPTS,
            error=last_error,
        )
        send_telegram_alert(error_message)
    print(settings.t("using_fallback_version", version=fallback_version))
    return fallback_version
