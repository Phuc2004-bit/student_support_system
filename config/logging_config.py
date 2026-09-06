import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import re

from config.settings import settings


_SENSITIVE_VALUE = re.compile(
    r"(?i)\b(password(?:_hash)?|db_password|pwd)\s*([=:])\s*([^\s;,]+)"
)


def redact_sensitive(text: str) -> str:
    return _SENSITIVE_VALUE.sub(r"\1\2***", text)


class RedactingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return redact_sensitive(super().format(record))


def setup_logging(log_dir: str | Path | None = None) -> Path:
    """Khởi tạo hệ thống logging cho ứng dụng."""

    target_dir = Path(log_dir) if log_dir is not None else settings.LOG_DIR
    target_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    log_file = target_dir / "app.log"

    formatter = RedactingFormatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    file_handler = RotatingFileHandler(
        filename=log_file,
        maxBytes=2_000_000,
        backupCount=5,
        encoding="utf-8",
    )

    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    root_logger = logging.getLogger()

    root_logger.setLevel(settings.LOG_LEVEL)

    for handler in root_logger.handlers[:]:
        if getattr(handler, "student_support_handler", False):
            root_logger.removeHandler(handler)
            handler.close()

    file_handler.student_support_handler = True
    console_handler.student_support_handler = True

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    return log_file
