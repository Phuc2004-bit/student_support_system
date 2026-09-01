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
from ui.pages.dashboard_page import DashboardPage
from ui.pages.placeholder_page import PlaceholderPage


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
            full_name="Admin",
            role=UserRole.ADMIN,
        ),
    )


def test_main_window_registers_real_dashboard_page():
    get_app()

    window = MainWindow(
        make_context()
    )

    dashboard = window.pages[
        "dashboard"
    ]

    assert isinstance(
        dashboard,
        DashboardPage,
    )
    assert (
        window.page_stack.page(
            "dashboard"
        )
        is dashboard
    )


def test_main_window_still_uses_placeholders_for_other_pages():
    get_app()

    window = MainWindow(
        make_context()
    )

    for key in (
        "students",
        "scores",
        "support",
        "reports",
        "catalogs",
        "system",
    ):
        assert isinstance(
            window.pages[key],
            PlaceholderPage,
        )


def test_dashboard_is_default_page_after_main_window_opens():
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
