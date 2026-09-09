"""Shared application-brand assets for source and frozen runtimes."""

from __future__ import annotations

from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QLabel

from config.paths import resource_path


APP_ICON_PARTS = ("assets", "app_icon.png")


def application_icon_path():
    """Return the bundled/development path for the official application icon."""

    return resource_path(*APP_ICON_PARTS)


def application_icon() -> QIcon:
    """Load the official icon without relying on the current working directory."""

    return QIcon(str(application_icon_path()))


def configure_application_icon(app: QApplication) -> QIcon:
    """Set the process-wide icon so top-level windows inherit one identity."""

    icon = application_icon()
    app.setWindowIcon(icon)
    return icon


def set_brand_icon(label: QLabel, logical_size: int) -> bool:
    """Render the shared mark in a compact branding label."""

    icon = QApplication.windowIcon()
    if icon.isNull():
        icon = application_icon()
    pixmap = icon.pixmap(QSize(logical_size, logical_size))
    if pixmap.isNull():
        return False
    label.setText("")
    label.setPixmap(pixmap)
    return True
