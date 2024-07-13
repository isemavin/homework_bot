class EmptyAnswer(Exception):
    """Пустой ответ от API."""

    pass


class RequestFailed(Exception):
    """Ошибка при запросе к API."""

    pass
