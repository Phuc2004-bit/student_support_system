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
    authenticated: bool = True,
) -> AppContext:
    session = None

    if authenticated:
        session = UserSession(
            user_id=1,
            username="admin",
            full_name="Quản trị viên",
            role=UserRole.ADMIN,
        )

    return AppContext(
        db=FakeDatabase(),
        auth_service=FakeAuthService(),
        permission_service=PermissionService(),
        session=session,
    )


def test_main_window_requires_authenticated_context():
    get_app()

    context = make_context(
        authenticated=False
    )

    with pytest.raises(PermissionError):
        MainWindow(context)


def test_main_window_builds_main_regions():
    get_app()

    window = MainWindow(
        make_context()
    )

    assert window.centralWidget() is not None
    assert window.topbar.objectName() == "topbar"
    assert window.sidebar.objectName() == "sidebar"
    assert (
        window.page_stack.objectName()
        == "pageStack"
    )


def test_main_window_uses_session_user_name():
    get_app()

    context = make_context()

    window = MainWindow(context)

    assert (
        window.topbar.user_label.text()
        == context.session.full_name
    )


def test_main_window_shell_dimensions_are_configured():
    get_app()

    window = MainWindow(
        make_context()
    )

    assert (
        window.sidebar.width()
        == MainWindow.SIDEBAR_WIDTH
    )
    assert (
        window.topbar.height()
        == MainWindow.TOPBAR_HEIGHT
    )


def test_main_window_uses_page_stack_instead_of_single_placeholder():
    get_app()

    window = MainWindow(
        make_context()
    )

    assert (
        window.page_stack.current_key
        == "dashboard"
    )
