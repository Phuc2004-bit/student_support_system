import os

from dotenv import load_dotenv

from config.paths import application_dir, environment_file_path, user_data_dir


BASE_DIR = application_dir()

load_dotenv(environment_file_path())


SUPPORTED_CHAT_PROVIDERS = frozenset({"offline", "gemini"})


def _chat_provider(value: str | None) -> str:
    normalized = (value or "offline").strip().lower()
    return normalized if normalized in SUPPORTED_CHAT_PROVIDERS else "offline"


def _bounded_float(
    value: str | None,
    default: float,
    minimum: float,
    maximum: float,
) -> float:
    try:
        parsed = float((value or "").strip())
    except (TypeError, ValueError):
        return default
    return parsed if minimum <= parsed <= maximum else default


def _bounded_int(
    value: str | None,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    try:
        parsed = int((value or "").strip())
    except (TypeError, ValueError):
        return default
    return parsed if minimum <= parsed <= maximum else default


class Settings:
    APP_NAME = os.getenv(
        "APP_NAME",
        "Hệ thống quản lý bổ trợ học tập",
    )

    APP_VERSION = os.getenv(
        "APP_VERSION",
        "1.3.0",
    )

    APP_ENV = os.getenv(
        "APP_ENV",
        "development",
    )

    LOG_LEVEL = os.getenv(
        "LOG_LEVEL",
        "INFO",
    ).upper()

    CHAT_ASSISTANT_ENABLED = os.getenv(
        "CHAT_ASSISTANT_ENABLED",
        "false",
    ).strip().lower() in {"1", "true", "yes", "on"}

    CHAT_PROVIDER = _chat_provider(os.getenv("CHAT_PROVIDER"))

    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

    GEMINI_MODEL = (
        os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
        or "gemini-2.5-flash"
    )

    GEMINI_TIMEOUT_SECONDS = _bounded_float(
        os.getenv("GEMINI_TIMEOUT_SECONDS"),
        default=15.0,
        minimum=1.0,
        maximum=60.0,
    )

    GEMINI_MAX_RETRIES = _bounded_int(
        os.getenv("GEMINI_MAX_RETRIES"),
        default=1,
        minimum=0,
        maximum=2,
    )

    LOG_DIR = user_data_dir() / "logs"


settings = Settings()
