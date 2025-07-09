"""Модуль для централизованного выполнения HTTP-запросов с повторными попытками."""

import time
import requests
import settings

# Создаем один экземпляр сессии для переиспользования TCP-соединений.
# Это повышает производительность, т.к. не нужно устанавливать новое
# TCP-соединение и проходить TLS-рукопожатие для каждого запроса.
_session = requests.Session()


def make_request(
    method: str,
    url: str,
    error_log_template: str,
    **kwargs,
) -> tuple[requests.Response | None, requests.RequestException | None]:
    """
    Выполняет HTTP-запрос с несколькими попытками в случае сбоя.

    Args:
        method: HTTP-метод ('GET', 'POST', и т.д.).
        url: URL для запроса.
        error_log_template: Шаблон сообщения об ошибке для логгирования в консоль.
        **kwargs: Дополнительные аргументы для requests (headers, json, timeout).

    Returns:
        Кортеж (Response, None) в случае успеха, иначе (None, Exception).
    """
    last_error = None
    # Устанавливаем таймаут по умолчанию из настроек, если он не передан явно.
    kwargs.setdefault("timeout", settings.API_TIMEOUT_SECONDS)

    for attempt in range(settings.API_RETRY_ATTEMPTS):
        try:
            response = _session.request(method, url, **kwargs)
            response.raise_for_status()
            return response, None  # Успех
        except requests.RequestException as e:
            last_error = e
            print(
                f"{settings.t('attempt_info', attempt=attempt + 1, total=settings.API_RETRY_ATTEMPTS)} "
                f"{error_log_template.format(e=e)}"
            )
            if attempt < settings.API_RETRY_ATTEMPTS - 1:
                time.sleep(settings.API_RETRY_DELAY_SECONDS)

    print(settings.t("all_attempts_failed"))
    return None, last_error  # Провал после всех попыток
