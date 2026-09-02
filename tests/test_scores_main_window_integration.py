import os
from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from app_context import AppContext
from bootstrap import build_app_context
from models.dto import (
    Assessment,
    ScoreBatchDetectionResult,
    ScoreRosterItem,
    UserSession,
)
from models.enums import AssessmentStatus, UserRole
from services.permission_service import PermissionService
from services.score_service import ScoreService
from ui.main_window import MainWindow
from ui.pages.dashboard_page import DashboardPage
from ui.pages.placeholder_page import PlaceholderPage
from ui.pages.scores_page import ScoresPage
from ui.pages.students_page import StudentsPage


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

    def list_classes_by_school_year(self, _year_id):
        return [(61, "6A1", 6, None, True)]

    def list_active_subjects(self):
        return [(11, "M1", "Môn 1")]

    def list_assessments(self, school_year_id, subject_id=None):
        return [Assessment(
            101, subject_id, school_year_id, "Giữa kỳ", 1, "MIDTERM",
            date(2026, 10, 1), AssessmentStatus.ACTIVE,
            datetime(2026, 9, 1),
        )]


class StudentListStub:
    def __init__(self):
        self.calls = 0

    def list_students(self, _filters=None):
        self.calls += 1
        return []


class ScoreStub:
    def __init__(self):
        self.rows = [
            ScoreRosterItem(71, "s1", "HS1", "Học sinh 1", 101, None, None)
        ]
        self.read_calls = 0
        self.save_calls = []
        self.intervention_creates = 0

    def list_score_roster(self, *_context):
        self.read_calls += 1
        return self.rows

    def create_scores_and_detect(self, entries):
        batch = tuple(entries)
        self.save_calls.append(batch)
        self.rows = [
            replace(row, score_id=901, score=batch[0].score_value)
            for row in self.rows
        ]
        self.intervention_creates += 1
        return ScoreBatchDetectionResult((), (object(),))


def make_context(role=UserRole.ADMIN, permission_service=None):
    return AppContext(
        db=object(),
        auth_service=object(),
        permission_service=permission_service or PermissionService(),
        session=UserSession(1, "user", "Người dùng", role),
        academic_service=AcademicStub(),
        student_list_service=StudentListStub(),
        student_service=object(),
        enrollment_service=object(),
        student_profile_service=object(),
        score_service=ScoreStub(),
    )


def select(combo, value):
    index = combo.findData(value)
    assert index >= 0
    combo.setCurrentIndex(index)


def test_bootstrap_composes_score_service_with_shared_database():
    context = build_app_context()
    assert isinstance(context.score_service, ScoreService)
    assert context.score_service.db is context.db


def test_main_window_registers_real_scores_page_with_dependencies():
    app()
    context = make_context()
    window = MainWindow(context)
    page = window.pages["scores"]

    assert isinstance(page, ScoresPage)
    assert not isinstance(page, PlaceholderPage)
    assert page.academic_service is context.academic_service
    assert page.enrollment_service is context.enrollment_service
    assert page.score_service is context.score_service
    assert isinstance(window.pages["students"], StudentsPage)
    assert isinstance(window.pages["dashboard"], DashboardPage)


@pytest.mark.parametrize("role", [UserRole.ADMIN, UserRole.TEACHER])
def test_admin_and_teacher_can_navigate_to_scores(role):
    app()
    window = MainWindow(make_context(role))

    assert window.can_navigate_to("scores") is True
    window.navigate_to("scores")
    assert window.page_stack.current_key == "scores"
    assert window.sidebar.current_key == "scores"


def test_sidebar_click_opens_scores_and_initializes_read_context():
    app()
    context = make_context()
    window = MainWindow(context)
    reads_before_navigation = context.academic_service.year_reads

    window.sidebar.button("scores").click()

    page = window.pages["scores"]
    assert window.page_stack.current_key == "scores"
    assert page.title_label.text() == "Điểm & Đánh giá"
    assert context.academic_service.year_reads == reads_before_navigation + 1


def test_programmatic_scores_navigation_cannot_bypass_permission():
    class DenyScoresPermission(PermissionService):
        @staticmethod
        def can_manage_scores(_session):
            return False

    app()
    window = MainWindow(make_context(
        UserRole.TEACHER, DenyScoresPermission()
    ))

    assert window.sidebar.button("scores").isHidden()
    assert window.can_navigate_to("scores") is False
    with pytest.raises(PermissionError):
        window.navigate_to("scores")
    assert window.page_stack.current_key == "dashboard"


def test_opening_scores_page_is_read_only():
    app()
    context = make_context()
    window = MainWindow(context)

    window.navigate_to("scores")

    assert context.score_service.save_calls == []
    assert context.score_service.intervention_creates == 0


def test_scores_save_from_main_window_uses_detection_aware_service():
    app()
    context = make_context()
    window = MainWindow(context)
    window.navigate_to("scores")
    page = window.pages["scores"]
    select(page.grade_combo, 6)
    select(page.class_combo, 61)
    select(page.subject_combo, 11)
    select(page.assessment_combo, 101)
    page.score_table.item(0, 3).setText("2.50")

    assert page.save_scores() is True
    assert len(context.score_service.save_calls) == 1
    assert context.score_service.read_calls == 2
    assert "Có 1 học sinh" in page.context_status_label.text()
