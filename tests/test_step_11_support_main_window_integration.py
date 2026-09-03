from dataclasses import replace
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from app_context import AppContext
from bootstrap import build_app_context
from models.dto import UserSession
from models.enums import InterventionStatus, UserRole
from services.academic_service import AcademicService
from services.permission_service import PermissionService
from services.report_service import ReportService
from services.support_service import SupportService
from services.user_service import UserService
from ui.dialogs.intervention_detail_dialog import InterventionDetailDialog
from ui.main_window import MainWindow
from ui.pages.placeholder_page import PlaceholderPage
from ui.pages.support_page import SupportPage
from tests.test_step_11_intervention_detail import detail


def app():
    return QApplication.instance() or QApplication([])


class AcademicStub:
    def __init__(self):
        self.year_reads = 0

    def list_school_years(self):
        self.year_reads += 1
        return [(2, "2026-2027", None, None, True)]

    def list_grades(self):
        return [(6, 6, "Khối 6")]

    def list_classes_by_school_year(self, _school_year_id):
        return [(61, "6A1", 6, None, True)]

    def list_active_subjects(self):
        return [(11, "M1", "Môn 1")]


class ReportStub:
    def __init__(self):
        self.calls = []

    def get_support_cases(self, **filters):
        self.calls.append(filters)
        return []


class SupportStub:
    def __init__(self):
        self.read_calls = []
        self.workflow_calls = []

    def get_intervention_detail(self, intervention_id):
        self.read_calls.append(intervention_id)
        return detail()

    def plan_intervention(self, *args, **kwargs):
        self.workflow_calls.append(("plan", args, kwargs))

    def start_intervention(self, *args, **kwargs):
        self.workflow_calls.append(("start", args, kwargs))

    def mark_waiting_review(self, *args, **kwargs):
        self.workflow_calls.append(("waiting", args, kwargs))

    def review_intervention(self, *args, **kwargs):
        self.workflow_calls.append(("review", args, kwargs))

    def continue_intervention(self, *args, **kwargs):
        self.workflow_calls.append(("continue", args, kwargs))


class UserStub:
    def list_active_teachers(self):
        return []


def make_context(role=UserRole.ADMIN, permission_service=None):
    return AppContext(
        db=object(),
        auth_service=object(),
        permission_service=permission_service or PermissionService(),
        session=UserSession(1, "user", "Người dùng", role),
        academic_service=AcademicStub(),
        report_service=ReportStub(),
        support_service=SupportStub(),
        user_service=UserStub(),
    )


def test_bootstrap_composes_support_dependencies_with_shared_database():
    context = build_app_context()

    assert isinstance(context.academic_service, AcademicService)
    assert isinstance(context.report_service, ReportService)
    assert isinstance(context.support_service, SupportService)
    assert isinstance(context.user_service, UserService)
    assert context.report_service.db is context.db
    assert context.support_service.db is context.db
    assert context.user_service.db is context.db


def test_main_window_registers_real_support_page_with_exact_dependencies():
    app()
    context = make_context()
    window = MainWindow(context)
    page = window.pages["support"]

    assert isinstance(page, SupportPage)
    assert not isinstance(page, PlaceholderPage)
    assert page.academic_service is context.academic_service
    assert page.support_read_service is context.report_service
    assert page.intervention_detail_service is context.support_service
    assert page.intervention_planning_service is context.support_service
    assert page.intervention_start_service is context.support_service
    assert page.intervention_waiting_review_service is context.support_service
    assert page.intervention_review_service is context.support_service
    assert page.intervention_continue_service is context.support_service
    assert page.assessment_service is context.academic_service
    assert page.user_service is context.user_service


@pytest.mark.parametrize("role", [UserRole.ADMIN, UserRole.TEACHER])
def test_admin_and_teacher_can_navigate_to_support(role):
    app()
    window = MainWindow(make_context(role))

    assert window.can_navigate_to("support") is True
    window.navigate_to("support")
    assert window.page_stack.current_key == "support"
    assert window.sidebar.current_key == "support"


def test_sidebar_opens_support_initializes_filters_and_title():
    app()
    context = make_context()
    window = MainWindow(context)
    reads_before = context.academic_service.year_reads

    window.sidebar.button("support").click()

    page = window.pages["support"]
    assert window.page_stack.current_key == "support"
    assert page.title_label.text() == "Bổ trợ học tập"
    assert context.academic_service.year_reads == reads_before + 1
    assert len(context.report_service.calls) == 1


def test_programmatic_support_navigation_cannot_bypass_permission():
    class DenySupportPermission(PermissionService):
        @staticmethod
        def can_manage_support(_session):
            return False

    app()
    window = MainWindow(make_context(
        UserRole.TEACHER,
        DenySupportPermission(),
    ))

    assert window.sidebar.button("support").isHidden()
    assert window.can_navigate_to("support") is False
    with pytest.raises(PermissionError):
        window.navigate_to("support")
    assert window.page_stack.current_key == "dashboard"


def test_invalid_session_cannot_open_main_window():
    app()
    context = make_context()
    context.clear_session()

    with pytest.raises(PermissionError):
        MainWindow(context)


def test_opening_support_is_read_only():
    app()
    context = make_context()
    window = MainWindow(context)

    window.navigate_to("support")

    assert context.report_service.calls
    assert context.support_service.read_calls == []
    assert context.support_service.workflow_calls == []


@pytest.mark.parametrize(
    ("status", "visible_button"),
    [
        (InterventionStatus.DETECTED, "plan_button"),
        (InterventionStatus.PLANNED, "start_button"),
        (InterventionStatus.IN_PROGRESS, "waiting_review_button"),
        (InterventionStatus.WAITING_REVIEW, "review_button"),
        (InterventionStatus.CONTINUE, "continue_button"),
        (InterventionStatus.COMPLETED, None),
    ],
)
def test_wired_support_workflow_exposes_only_action_for_status(
    status,
    visible_button,
):
    app()
    context = make_context()
    window = MainWindow(context)
    page = window.pages["support"]
    value = replace(detail(), status=status)
    reader = type("Reader", (), {
        "get_intervention_detail": lambda self, _id: value,
    })()
    dialog = InterventionDetailDialog(
        101,
        reader,
        planning_service=page.intervention_planning_service,
        start_service=page.intervention_start_service,
        waiting_review_service=page.intervention_waiting_review_service,
        review_service=page.intervention_review_service,
        continue_service=page.intervention_continue_service,
        assessment_service=page.assessment_service,
        user_service=page.user_service,
    )

    dialog.load_detail()

    action_names = (
        "plan_button",
        "start_button",
        "waiting_review_button",
        "review_button",
        "continue_button",
    )
    visible = [
        name for name in action_names
        if not getattr(dialog, name).isHidden()
    ]
    assert visible == ([] if visible_button is None else [visible_button])
    assert context.support_service.workflow_calls == []
