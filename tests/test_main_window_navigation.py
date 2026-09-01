import os

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


def make_context() -> AppContext:
    return AppContext(
        db=FakeDatabase(),
        auth_service=FakeAuthService(),
        permission_service=PermissionService(),
        session=UserSession(
            user_id=1,
            username="admin",
            full_name="Quản trị viên",
            role=UserRole.ADMIN,
        ),
    )


def test_main_window_registers_all_sidebar_pages():
    get_app()

    window = MainWindow(
        make_context()
    )

    assert set(window.pages) == {
        "dashboard",
        "students",
        "scores",
        "support",
        "reports",
        "catalogs",
        "system",
    }


def test_main_window_starts_on_dashboard():
    get_app()

    window = MainWindow(
        make_context()
    )

    assert (
        window.page_stack.current_key
        == "dashboard"
    )
    assert (
        window.sidebar.current_key
        == "dashboard"
    )


def test_sidebar_click_changes_current_page():
    get_app()

    window = MainWindow(
        make_context()
    )

    window.sidebar.button(
        "students"
    ).click()

    assert (
        window.page_stack.current_key
        == "students"
    )
    assert (
        window.sidebar.current_key
        == "students"
    )


def test_programmatic_navigation_keeps_sidebar_synced():
    get_app()

    window = MainWindow(
        make_context()
    )

    window.navigate_to(
        "reports"
    )

    assert (
        window.page_stack.current_key
        == "reports"
    )
    assert (
        window.sidebar.current_key
        == "reports"
    )
