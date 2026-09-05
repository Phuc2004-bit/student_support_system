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
from ui.pages.catalog_page import CatalogPage
from ui.pages.reports_page import ReportsPage
from ui.pages.students_page import StudentsPage
from ui.pages.scores_page import ScoresPage
from ui.pages.support_page import SupportPage
from ui.pages.system_page import SystemPage


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


def test_main_window_uses_all_real_pages_after_step_12_9():
    get_app()

    window = MainWindow(
        make_context()
    )

    assert isinstance(window.pages["students"], StudentsPage)
    assert isinstance(window.pages["scores"], ScoresPage)
    assert isinstance(window.pages["support"], SupportPage)

    assert isinstance(window.pages["reports"], ReportsPage)
    assert isinstance(window.pages["catalogs"], CatalogPage)
    assert isinstance(window.pages["system"], SystemPage)


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
