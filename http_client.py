"""Модуль для централизованного выполнения HTTP-запросов с повторными попытками."""

import time
import random
import requests
import settings


class ApiClientError(Exception):
    """Исключение, которое выбрасывается, когда HTTP-клиент не может выполнить запрос после всех попыток."""


# Создаем один экземпляр сессии для переиспользования TCP-соединений.
# Это повышает производительность, т.к. не нужно устанавливать новое
# TCP-соединение и проходить TLS-рукопожатие для каждого запроса.
_session = requests.Session()


def make_request(
    method: str,
    url: str,
    error_log_template: str,
    **kwargs,
) -> requests.Response:
    """
    Выполняет HTTP-запрос с несколькими попытками в случае сбоя.
    Использует стратегию экспоненциальной задержки с джиттером.

    Args:
        method: HTTP-метод ('GET', 'POST', и т.д.).
        url: URL для запроса.
        error_log_template: Шаблон сообщения об ошибке для логгирования в консоль.
        **kwargs: Дополнительные аргументы для requests (headers, json, timeout).

    Returns:
        Объект requests.Response в случае успеха.

    Raises:
        ApiClientError: Если запрос не удался после всех попыток.
    """
    last_error = None
    # Устанавливаем таймаут по умолчанию из настроек, если он не передан явно.
    kwargs.setdefault("timeout", settings.API_TIMEOUT_SECONDS)

    for attempt in range(settings.API_RETRY_ATTEMPTS):
        try:
            response = _session.request(method, url, **kwargs)
            response.raise_for_status()
            return response  # Успех
        except requests.RequestException as e:
            last_error = e
            print(
                f"{settings.t('attempt_info', attempt=attempt + 1, total=settings.API_RETRY_ATTEMPTS)} "
                f"{error_log_template.format(e=e)}"
            )
            if attempt < settings.API_RETRY_ATTEMPTS - 1:
                # Экспоненциальная задержка с джиттером для предотвращения "волн" нагрузки
                backoff_time = settings.API_RETRY_DELAY_SECONDS * (2**attempt)
                jitter = random.uniform(0, 1)
                sleep_time = backoff_time + jitter
                print(settings.t("retry_in_seconds", delay=round(sleep_time, 2)))
                time.sleep(sleep_time)

    # Формируем и выбрасываем кастомное исключение, если все попытки провалились
    final_error_message = settings.t("all_attempts_failed_with_error", error=last_error)
    print(final_error_message)
    raise ApiClientError(final_error_message) from last_error
