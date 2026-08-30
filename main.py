import logging
import sys

from PySide6.QtWidgets import QApplication, QLabel

from config.logging_config import setup_logging
from config.settings import settings


def main() -> int:
    setup_logging()

    logger = logging.getLogger(__name__)

    logger.info(
        "Starting %s v%s",
        settings.APP_NAME,
        settings.APP_VERSION,
    )

    app = QApplication(sys.argv)

    app.setApplicationName(settings.APP_NAME)
    app.setApplicationVersion(settings.APP_VERSION)

    # Cửa sổ tạm để kiểm tra foundation.
    label = QLabel(
        "Student Support System\n"
        "Foundation OK"
    )

    label.setWindowTitle(settings.APP_NAME)
    label.resize(500, 150)
    label.show()

    exit_code = app.exec()

    logger.info(
        "Application stopped with exit code %s",
        exit_code,
    )

    return exit_code


if __name__ == "__main__":
    sys.exit(main())