import inspect
import os
from datetime import date, datetime

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QComboBox

from models.dto.assessment import Assessment
from models.enums import AssessmentStatus
from ui.pages.scores_page import ScoresPage


def app():
    return QApplication.instance() or QApplication([])


def assessment(
    assessment_id=101,
    subject_id=11,
    school_year_id=2,
    name="Giữa kỳ",
):
    return Assessment(
        assessment_id=assessment_id,
        subject_id=subject_id,
        school_year_id=school_year_id,
        assessment_name=name,
        semester=1,
        assessment_type="MIDTERM",
        assessment_date=date(2026, 10, 10),
        status=AssessmentStatus.ACTIVE,
        created_at=datetime(2026, 9, 1),
    )


class AcademicStub:
    def __init__(self):
        self.year_calls = 0
        self.grade_calls = 0
        self.class_calls = []
        self.subject_calls = 0
        self.assessment_calls = []

    def list_school_years(self):
        self.year_calls += 1
        return [
            (1, "2025-2026", None, None, False),
            (2, "2026-2027", None, None, True),
        ]

    def list_grades(self):
        self.grade_calls += 1
        return [(6, 6, "Khối 6"), (7, 7, "Khối 7")]

    def list_classes_by_school_year(self, school_year_id):
        self.class_calls.append(school_year_id)
        return {
            1: [(51, "6A0", 6, None, True)],
            2: [
                (61, "6A1", 6, None, True),
                (62, "6A2", 6, None, True),
                (71, "7A1", 7, None, True),
            ],
        }.get(school_year_id, [])

    def list_active_subjects(self):
        self.subject_calls += 1
        return [(11, "M1", "Môn 1"), (12, "M2", "Môn 2")]

    def list_assessments(self, school_year_id, subject_id=None):
        self.assessment_calls.append((school_year_id, subject_id))
        return [
            assessment(
                school_year_id=school_year_id,
                subject_id=subject_id,
            )
        ]


def select_data(combo, value):
    index = combo.findData(value)
    assert index >= 0
    combo.setCurrentIndex(index)


def complete_context(page):
    select_data(page.grade_combo, 6)
    select_data(page.class_combo, 61)
    select_data(page.subject_combo, 11)
    select_data(page.assessment_combo, 101)


def test_scores_page_initializes_with_five_context_controls():
    app()
    page = ScoresPage()

    controls = (
        page.school_year_combo,
        page.grade_combo,
        page.class_combo,
        page.subject_combo,
        page.assessment_combo,
    )

    assert all(isinstance(control, QComboBox) for control in controls)
    assert page.score_table_placeholder.objectName() == (
        "scoreTablePlaceholder"
    )
    assert page.current_context().is_complete is False


def test_initialize_loads_school_years_and_current_year():
    app()
    service = AcademicStub()
    page = ScoresPage(academic_service=service)

    assert page.initialize_scores() is True
    assert service.year_calls == 1
    assert page.school_year_combo.currentData() == 2
    assert page.grade_combo.isEnabled()
    assert page.class_combo.isEnabled() is False


def test_grade_change_loads_only_matching_classes():
    app()
    service = AcademicStub()
    page = ScoresPage(academic_service=service)
    page.initialize_scores()

    select_data(page.grade_combo, 6)

    assert service.class_calls == [2]
    assert page.class_combo.count() == 3
    assert page.class_combo.itemData(1) == 61
    assert page.class_combo.itemData(2) == 62
    assert page.subject_combo.isEnabled() is False


def test_upstream_change_resets_dependent_context():
    app()
    service = AcademicStub()
    page = ScoresPage(academic_service=service)
    page.initialize_scores()
    complete_context(page)

    select_data(page.school_year_combo, 1)

    assert page.grade_combo.currentData() is None
    assert page.class_combo.currentData() is None
    assert page.subject_combo.currentData() is None
    assert page.assessment_combo.currentData() is None
    assert page.current_context().is_complete is False


def test_subject_change_queries_assessments_by_year_and_subject():
    app()
    service = AcademicStub()
    page = ScoresPage(academic_service=service)
    page.initialize_scores()

    select_data(page.grade_combo, 6)
    select_data(page.class_combo, 61)
    select_data(page.subject_combo, 12)

    assert service.assessment_calls == [(2, 12)]
    assert page.assessment_combo.count() == 2
    assert page.assessment_combo.itemData(1) == 101


def test_complete_context_updates_page_state():
    app()
    page = ScoresPage(academic_service=AcademicStub())
    page.initialize_scores()
    complete_context(page)

    assert page.current_context().is_complete is True
    assert page.context_status_label.text() == "Đã chọn đầy đủ ngữ cảnh."


class EmptyAcademicStub:
    def list_school_years(self):
        return []

    def list_grades(self):
        return []

    def list_classes_by_school_year(self, _school_year_id):
        return []

    def list_active_subjects(self):
        return []

    def list_assessments(self, _school_year_id, subject_id=None):
        return []


def test_empty_academic_data_does_not_crash():
    app()
    page = ScoresPage(academic_service=EmptyAcademicStub())

    assert page.initialize_scores() is True
    assert page.school_year_combo.count() == 1
    assert page.school_year_combo.currentData() is None
    assert page.current_context().is_complete is False


def test_page_without_service_remains_in_incomplete_state():
    app()
    page = ScoresPage()

    assert page.initialize_scores() is False
    assert page.current_context().is_complete is False
    assert page.school_year_combo.isEnabled() is False


def test_scores_page_has_no_score_support_or_sql_dependencies():
    source = inspect.getsource(ScoresPage).upper()

    assert "SCORESERVICE" not in source
    assert "SUPPORTSERVICE" not in source
    assert "CREATE_SCORE" not in source
    assert "SELECT " not in source
    assert "INSERT " not in source
