from __future__ import annotations

import os
from pathlib import Path
import sys


PRODUCT_DIRECTORY = "StudentSupportSystem"
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def is_frozen() -> bool:
    """Return whether the process is running from a PyInstaller bundle."""

    return bool(getattr(sys, "frozen", False))


def application_dir() -> Path:
    """Directory for deployment-time files such as an external ``.env``."""

    if is_frozen():
        return Path(sys.executable).resolve().parent
    return PROJECT_ROOT


def bundled_resource_dir() -> Path:
    """Base directory for read-only files bundled by PyInstaller."""

    if is_frozen():
        bundle_dir = getattr(sys, "_MEIPASS", None)
        if bundle_dir:
            return Path(bundle_dir).resolve()
    return PROJECT_ROOT


def resource_path(*parts: str) -> Path:
    """Resolve a read-only resource in development and frozen modes."""

    return bundled_resource_dir().joinpath(*parts)


def environment_file_path() -> Path:
    """Keep runtime configuration external to the executable bundle."""

    return application_dir() / ".env"


def user_data_dir() -> Path:
    """Return the per-user writable application directory on Windows."""

    local_app_data = os.getenv("LOCALAPPDATA", "").strip()
    base = Path(local_app_data) if local_app_data else Path.home() / "AppData" / "Local"
    return base / PRODUCT_DIRECTORY
