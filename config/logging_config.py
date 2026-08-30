import logging
from logging.handlers import RotatingFileHandler

from config.settings import settings


def setup_logging() -> None:
    """Khởi tạo hệ thống logging cho ứng dụng."""

    settings.LOG_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    log_file = settings.LOG_DIR / "app.log"

    formatter = logging.Formatter(
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

    root_logger.handlers.clear()

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)