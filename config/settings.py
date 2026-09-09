import os

from dotenv import load_dotenv

from config.paths import application_dir, environment_file_path, user_data_dir


BASE_DIR = application_dir()

load_dotenv(environment_file_path())


class Settings:
    APP_NAME = os.getenv(
        "APP_NAME",
        "Hệ thống quản lý bổ trợ học tập",
    )

    APP_VERSION = os.getenv(
        "APP_VERSION",
        "1.1.0",
    )

    APP_ENV = os.getenv(
        "APP_ENV",
        "development",
    )

    LOG_LEVEL = os.getenv(
        "LOG_LEVEL",
        "INFO",
    ).upper()

    LOG_DIR = user_data_dir() / "logs"


settings = Settings()
