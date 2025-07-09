"""
Модуль для взаимодействия с API ZeroTier и получения информации о членах сетей, а также о последней версии ZeroTier.
Содержит функции с поддержкой повторных попыток и уведомлений в случае ошибок.
"""

import time
import settings
import database_manager as db
from send_to_chat import send_telegram_alert
from http_client import ApiClientError, make_request


def get_members(token: str, network_id: str) -> list | None:
    """Получает список участников для одной сети ZeroTier с несколькими попытками."""
    url = f"{settings.API_URL}network/{network_id}/member"
    headers = {"Authorization": f"Bearer {token}"}
    error_log_template = settings.t("error_getting_members", net_id=network_id, e="{e}")

    try:
        response = make_request("GET", url, error_log_template, headers=headers)
        return response.json()
    except ApiClientError as e:
        # Если после всех попыток произошла ошибка, отправляем уведомление
        error_message = settings.t(
            "alert_failed_to_get_members",
            net_id=network_id,
            attempts=settings.API_RETRY_ATTEMPTS,
            error=e,
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
            time.sleep(1)  # Небольшая задержка между запросами к разным сетям
    return all_members


def get_latest_zerotier_version() -> str:
    """
    Получает последнюю версию ZeroTier с GitHub API.
    В случае успеха обновляет значение в БД.
    В случае ошибки пытается получить значение из БД, и только потом использует fallback.
    """
    url = "https://api.github.com/repos/zerotier/ZeroTierOne/releases/latest"
    error_log_template = settings.t("error_getting_latest_version", e="{e}")

    try:
        response = make_request("GET", url, error_log_template)
        try:
            data = response.json()
            # Теги на GitHub часто имеют префикс 'v', уберем его
            latest_version = data["tag_name"].lstrip("v")
            # При успехе сохраняем в БД
            db.save_latest_zt_version(latest_version)
            return latest_version
        except (KeyError, ValueError) as parse_error:
            # Ошибка парсинга ответа, даже если запрос прошел успешно
            # Создаем новое исключение, чтобы передать его дальше
            raise ApiClientError(
                f"Failed to parse GitHub API response: {parse_error}"
            ) from parse_error
    except ApiClientError as e:
        # Если после всех попыток произошла ошибка, отправляем уведомление
        send_telegram_alert(
            settings.t(
                "alert_failed_to_get_latest_version",
                attempts=settings.API_RETRY_ATTEMPTS,
                error=e,
            )
        )

    # Если API недоступен, пытаемся взять версию из БД
    db_version = db.get_latest_zt_version_from_db()
    if db_version:
        print(settings.t("using_db_version", version=db_version))
        return db_version

    # Если и в БД ничего нет, используем fallback из настроек
    print(settings.t("using_fallback_version", version=settings.ZT_FALLBACK_VERSION))
    return settings.ZT_FALLBACK_VERSION
