import contextvars
import logging
from contextlib import contextmanager
from typing import Any

_request_context: contextvars.ContextVar[dict[str, Any]] = contextvars.ContextVar(
    "request_context",
    default={},
)

_LOG_FORMAT = (
    "%(asctime)s %(levelname)s "
    "[%(service_name)s:%(environment)s] "
    "[request_id=%(request_id)s] "
    "%(name)s: %(message)s"
)


class RequestContextFilter(logging.Filter):
    """Добавляет контекст запроса в записи стандартного журнала."""

    def __init__(self, *, service_name: str, environment: str) -> None:
        super().__init__()
        self.service_name = service_name
        self.environment = environment

    def filter(self, record: logging.LogRecord) -> bool:
        record.service_name = self.service_name
        record.environment = self.environment
        record.request_id = "-"

        context = _request_context.get()
        for key, value in context.items():
            setattr(record, key, value)
        return True


def _install_request_context_filter(*, service_name: str, environment: str) -> None:
    context_filter = RequestContextFilter(
        service_name=service_name,
        environment=environment,
    )
    root_logger = logging.getLogger()
    root_logger.filters = [
        logger_filter
        for logger_filter in root_logger.filters
        if not isinstance(logger_filter, RequestContextFilter)
    ]
    root_logger.addFilter(context_filter)
    for handler in root_logger.handlers:
        handler.addFilter(context_filter)


def _apply_log_level_rules(log_level_rules: str) -> None:
    for rule in log_level_rules.split(","):
        rule = rule.strip()
        if not rule:
            continue

        logger_name, level_name = rule.split(":", maxsplit=1)
        logging.getLogger(logger_name.strip()).setLevel(level_name.strip().upper())


def setup_logging(*, service_name: str, environment: str, log_level_rules: str = "") -> None:
    """Инициализирует логирование через встроенную библиотеку logging."""

    logging.basicConfig(
        level=logging.INFO,
        format=_LOG_FORMAT,
        force=True,
    )
    _install_request_context_filter(
        service_name=service_name,
        environment=environment,
    )
    _apply_log_level_rules(log_level_rules)


@contextmanager
def with_request_context(**context: Any):
    """Добавляет контекст (например, request_id) ко всем логам в блоке."""
    current_context = dict(_request_context.get())
    current_context.update(context)
    token = _request_context.set(current_context)
    try:
        yield
    finally:
        _request_context.reset(token)
