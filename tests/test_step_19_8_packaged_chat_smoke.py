from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from app_context import AppContext
from assistant import ChatAssistantService
from assistant.providers.offline_provider import OfflineProvider
from build_config import packaged_runtime_smoke
from models.dto import UserSession
from models.enums import UserRole
from services.permission_service import PermissionService
from ui.main_window import MainWindow


ROOT = Path(__file__).resolve().parent.parent


def app() -> QApplication:
    return QApplication.instance() or QApplication([])


def context() -> AppContext:
    return AppContext(
        db=object(),
        auth_service=object(),
        permission_service=PermissionService(),
        session=UserSession(1, "actor", "Người dùng", UserRole.ADMIN),
    )


@pytest.mark.parametrize("enabled", [False, True])
def test_packaged_chat_harness_checks_disabled_and_enabled_paths(
    monkeypatch, enabled
):
    application = app()
    monkeypatch.setattr(
        packaged_runtime_smoke.settings,
        "CHAT_ASSISTANT_ENABLED",
        enabled,
    )
    window = MainWindow(
        context(),
        chat_assistant_enabled=enabled,
        chat_assistant_service=ChatAssistantService(provider=OfflineProvider()),
    )
    try:
        window.show()
        application.processEvents()
        results = packaged_runtime_smoke._run_chat_checks(application, window)
        assert results
        assert all(value is True for value in results.values())
    finally:
        window.close()


def test_packaged_chat_harness_uses_no_network_or_business_dependency():
    source = (ROOT / "build_config" / "packaged_runtime_smoke.py").read_text(
        encoding="utf-8"
    )

    chat_section = source.split("def _run_chat_checks", 1)[1].split(
        "def _run_checks", 1
    )[0]
    assert ".generate_content(" not in chat_section
    assert "requests." not in chat_section
    assert "repositories" not in chat_section
    assert "support_service" not in chat_section
    assert "student_service" not in chat_section
    assert "password_hash" not in chat_section
