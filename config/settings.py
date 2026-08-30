import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


class Settings:
    APP_NAME = os.getenv(
        "APP_NAME",
        "Hệ thống quản lý bổ trợ học tập",
    )

    APP_VERSION = os.getenv(
        "APP_VERSION",
        "1.0.0",
    )

    APP_ENV = os.getenv(
        "APP_ENV",
        "development",
    )

    LOG_LEVEL = os.getenv(
        "LOG_LEVEL",
        "INFO",
    ).upper()

    LOG_DIR = BASE_DIR / "logs"


settings = Settings()