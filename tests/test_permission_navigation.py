import os

import pytest

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PySide6.QtWidgets import QApplication

from app_context import AppContext
from models.dto import UserSession
from models.enums import UserRole
from services.permission_service import PermissionService
from ui.main_window import MainWindow


def get_app() -> QApplication:
    app = QApplication.instance()

    if app is None:
        app = QApplication([])

    return app


class FakeDatabase:
    pass


class FakeAuthService:
    pass


def make_context(
    role: UserRole,
) -> AppContext:
    return AppContext(
        db=FakeDatabase(),
        auth_service=FakeAuthService(),
        permission_service=PermissionService(),
        session=UserSession(
            user_id=1,
            username="user",
            full_name="Người dùng thử",
            role=role,
        ),
    )


def test_admin_sees_all_navigation_items():
    get_app()

    window = MainWindow(
        make_context(UserRole.ADMIN)
    )

    for key in (
        "dashboard",
        "students",
        "scores",
        "support",
        "reports",
        "catalogs",
        "system",
    ):
        assert not window.sidebar.button(
            key
        ).isHidden()
        assert window.can_navigate_to(
            key
        ) is True


def test_teacher_navigation_visibility_matches_permissions():
    get_app()

    window = MainWindow(
        make_context(UserRole.TEACHER)
    )

    for key in (
        "dashboard",
        "students",
        "scores",
        "support",
        "reports",
    ):
        assert not window.sidebar.button(
            key
        ).isHidden()
        assert window.can_navigate_to(
            key
        ) is True

    for key in (
        "catalogs",
        "system",
    ):
        assert window.sidebar.button(
            key
        ).isHidden()
        assert window.can_navigate_to(
            key
        ) is False


def test_teacher_cannot_navigate_to_catalogs_programmatically():
    get_app()

    window = MainWindow(
        make_context(UserRole.TEACHER)
    )

    with pytest.raises(PermissionError):
        window.navigate_to(
            "catalogs"
        )

    assert (
        window.page_stack.current_key
        == "dashboard"
    )


def test_teacher_cannot_navigate_to_system_programmatically():
    get_app()

    window = MainWindow(
        make_context(UserRole.TEACHER)
    )

    with pytest.raises(PermissionError):
        window.navigate_to(
            "system"
        )

    assert (
        window.page_stack.current_key
        == "dashboard"
    )


def test_teacher_can_navigate_to_allowed_page():
    get_app()

    window = MainWindow(
        make_context(UserRole.TEACHER)
    )

    window.navigate_to(
        "support"
    )

    assert (
        window.page_stack.current_key
        == "support"
    )
    assert (
        window.sidebar.current_key
        == "support"
    )


def test_unknown_page_is_rejected_before_permission_check():
    get_app()

    window = MainWindow(
        make_context(UserRole.ADMIN)
    )

    with pytest.raises(KeyError):
        window.can_navigate_to(
            "unknown"
        )
