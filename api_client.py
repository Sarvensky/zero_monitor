import requests
from send_to_chat import send_telegram_alert
import settings
import time


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
                f"Попытка {attempt + 1}/{settings.API_RETRY_ATTEMPTS}: Ошибка при получении участников сети {network_id}: {e}"
            )
            if attempt < settings.API_RETRY_ATTEMPTS - 1:
                print(
                    f"Повторная попытка через {settings.API_RETRY_DELAY_SECONDS} сек..."
                )
                time.sleep(settings.API_RETRY_DELAY_SECONDS)
            else:
                print("Все попытки исчерпаны.")
    # Отправляем уведомление только после того, как все попытки провалились
    if last_error:
        error_message = f"⛔ Не удалось получить участников сети {network_id} после {settings.API_RETRY_ATTEMPTS} попыток. Последняя ошибка: {last_error}"
        send_telegram_alert(error_message)
    return None


def get_all_members(networks: list[dict]) -> list[dict]:
    """Получает и объединяет участников из всех указанных сетей ZeroTier."""
    print("Получение информации о членах сети ZeroTier...")
    all_members = []
    num_networks = len(networks)
    for i, network in enumerate(networks):
        members = get_members(network["token"], network["network_id"])
        if members:
            all_members.extend(members)
        else:
            print(f"Не удалось получить участников для сети {network['network_id']}")

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
                f"Попытка {attempt + 1}/{settings.API_RETRY_ATTEMPTS}: Ошибка при получении последней версии ZeroTier: {e}"
            )
            if attempt < settings.API_RETRY_ATTEMPTS - 1:
                print(
                    f"Повторная попытка через {settings.API_RETRY_DELAY_SECONDS} сек..."
                )
                time.sleep(settings.API_RETRY_DELAY_SECONDS)
            else:
                print("Все попытки исчерпаны.")
    # Отправляем уведомление только после того, как все попытки провалились
    if last_error:
        error_message = f"⛔ Не удалось получить последнюю версию ZeroTier после {settings.API_RETRY_ATTEMPTS} попыток. Последняя ошибка: {last_error}"
        send_telegram_alert(error_message)
    print(f"Используется версия по умолчанию: {fallback_version}")
    return fallback_version
