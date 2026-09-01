import os
from datetime import date
from inspect import signature
from unittest.mock import Mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app_context import AppContext
from models.dto import UserSession
from models.enums import UserRole
from models.dto.dashboard_dto import (
    DashboardData,
    DashboardSummary,
)
from ui.main_window import MainWindow


def get_app():
    app = QApplication.instance()
    return app or QApplication([])


class PermissionStub:
    @staticmethod
    def _role_value(session):
        return getattr(session.role, "value", session.role)

    def can_manage_users(self, session):
        return self._role_value(session) == "ADMIN"

    def can_manage_catalogs(self, session):
        return self._role_value(session) == "ADMIN"

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
        return [
            (
                2,
                "2026-2027",
                date(2026, 9, 1),
                date(2027, 5, 31),
                True,
            )
        ]

    def list_grades(self):
        return []

    def list_active_subjects(self):
        return []

    def list_classes_by_school_year(self, school_year_id):
        return []


class DashboardStub:
    def __init__(self):
        self.call_count = 0

    def get_dashboard(self, **kwargs):
        self.call_count += 1
        return DashboardData(
            summary=DashboardSummary(
                total_students=1000,
                needs_support_count=100,
                in_progress_count=40,
                waiting_review_count=10,
                completed_count=30,
                continue_count=20,
            ),
            status_breakdown=(),
            attention_items=(),
        )


def make_session(role_name):
    params = signature(UserSession).parameters
    values = {
        "user_id": 1,
        "username": "tester",
        "full_name": "Người dùng thử",
        "role": UserRole(role_name),
        "email": None,
        "phone": None,
    }
    return UserSession(
        **{
            key: value
            for key, value in values.items()
            if key in params
        }
    )


def make_context(role_name):
    dashboard_service = DashboardStub()
    context = AppContext(
        db=Mock(),
        auth_service=Mock(),
        permission_service=PermissionStub(),
        session=make_session(role_name),
        academic_service=AcademicStub(),
        dashboard_service=dashboard_service,
    )
    return context, dashboard_service


def test_main_window_starts_on_loaded_dashboard():
    get_app()
    context, dashboard_service = make_context("ADMIN")

    window = MainWindow(context)

    assert window.page_stack.current_key == "dashboard"
    assert dashboard_service.call_count == 1
    assert (
        window.pages["dashboard"]
        .kpi_cards["total_students"]
        .value
        == 1000
    )


def test_teacher_dashboard_and_logout_still_work_end_to_end():
    get_app()
    context, dashboard_service = make_context("TEACHER")

    window = MainWindow(context)

    assert window.can_navigate_to("dashboard") is True
    assert window.can_navigate_to("catalogs") is False
    assert window.can_navigate_to("system") is False
    assert dashboard_service.call_count == 1

    window.request_logout()

    assert context.session is None
