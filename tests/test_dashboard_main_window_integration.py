import os
from unittest.mock import Mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app_context import AppContext
from models.dto import UserSession
from models.enums import UserRole
from ui.main_window import MainWindow
from ui.pages.dashboard_page import DashboardPage


def get_app():
    app = QApplication.instance()
    return app or QApplication([])


class PermissionStub:
    def can_manage_users(self, session):
        return getattr(session.role, "value", session.role) == "ADMIN"

    def can_manage_catalogs(self, session):
        return getattr(session.role, "value", session.role) == "ADMIN"

    def can_manage_students(self, session):
        return True

    def can_manage_scores(self, session):
        return True

    def can_manage_support(self, session):
        return True

    def can_view_reports(self, session):
        return True


class AcademicStub:
    def list_school_years(self):
        return []

    def list_grades(self):
        return []

    def list_active_subjects(self):
        return []

    def list_classes_by_school_year(self, school_year_id):
        return []


def make_session(role):
    # Avoid depending on constructor details beyond existing DTO fields:
    from inspect import signature

    params = signature(UserSession).parameters
    values = {
        "user_id": 1,
        "username": "tester",
        "full_name": "Người dùng thử",
        "role": UserRole(role),
        "email": None,
        "phone": None,
    }
    return UserSession(
        **{k: v for k, v in values.items() if k in params}
    )


def make_context(role):
    return AppContext(
        db=Mock(),
        auth_service=Mock(),
        permission_service=PermissionStub(),
        session=make_session(role),
        academic_service=AcademicStub(),
        dashboard_service=Mock(),
    )


def test_main_window_injects_dashboard_dependencies():
    get_app()
    context = make_context("ADMIN")
    window = MainWindow(context)

    page = window.pages["dashboard"]

    assert isinstance(page, DashboardPage)
    assert page.academic_service is context.academic_service
    assert page.dashboard_service is context.dashboard_service


def test_admin_can_navigate_dashboard_after_integration():
    get_app()
    window = MainWindow(make_context("ADMIN"))

    assert window.can_navigate_to("dashboard") is True
    assert window.page_stack.current_key == "dashboard"


def test_teacher_can_navigate_dashboard_after_integration():
    get_app()
    window = MainWindow(make_context("TEACHER"))

    assert window.can_navigate_to("dashboard") is True
    assert window.page_stack.current_key == "dashboard"
    assert window.can_navigate_to("catalogs") is False
    assert window.can_navigate_to("system") is False
