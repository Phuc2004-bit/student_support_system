import inspect
import os
from datetime import date, datetime
from decimal import Decimal

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from exceptions import DuplicateError
from models.dto.assessment import Assessment
from models.dto.enrollment import EnrollmentListItem
from models.enums import AssessmentStatus, EnrollmentStatus
from ui.pages.scores_page import ScoresPage


def app():
    return QApplication.instance() or QApplication([])


class AcademicStub:
    def list_school_years(self):
        return [(2, "2026-2027", None, None, True)]

    def list_grades(self):
        return [(6, 6, "Khối 6")]

    def list_classes_by_school_year(self, _school_year_id):
        return [(61, "6A1", 6, None, True)]

    def list_active_subjects(self):
        return [(11, "M1", "Môn 1")]

    def list_assessments(self, school_year_id, subject_id=None):
        return [
            Assessment(
                assessment_id=101,
                subject_id=subject_id,
                school_year_id=school_year_id,
                assessment_name="Giữa kỳ",
                semester=1,
                assessment_type="MIDTERM",
                assessment_date=date(2026, 10, 10),
                status=AssessmentStatus.ACTIVE,
                created_at=datetime(2026, 9, 1),
            )
        ]


def enrollment(enrollment_id, code, name):
    return EnrollmentListItem(
        enrollment_id=enrollment_id,
        student_id=f"student-{enrollment_id}",
        student_code=code,
        full_name=name,
        class_id=61,
        class_name="6A1",
        grade_number=6,
        school_year_id=2,
        school_year_name="2026-2027",
        status=EnrollmentStatus.ACTIVE,
    )


class EnrollmentStub:
    def __init__(self, result=None, error=None):
        self.result = list(
            result
            if result is not None
            else (
                enrollment(701, "HS01", "Học sinh 1"),
                enrollment(702, "HS02", "Học sinh 2"),
            )
        )
        self.error = error
        self.calls = []

    def list_class_enrollments(self, class_id, school_year_id):
        self.calls.append((class_id, school_year_id))
        if self.error is not None:
            raise self.error
        return self.result


class ScoreStub:
    def __init__(self, error=None):
        self.error = error
        self.calls = []

    def create_scores(self, entries):
        batch = tuple(entries)
        self.calls.append(batch)
        if self.error is not None:
            raise self.error
        return [object() for _entry in batch]


def select_data(combo, value):
    index = combo.findData(value)
    assert index >= 0
    combo.setCurrentIndex(index)


def complete_context(page):
    page.initialize_scores()
    select_data(page.grade_combo, 6)
    select_data(page.class_combo, 61)
    select_data(page.subject_combo, 11)
    select_data(page.assessment_combo, 101)


def make_page(enrollment_service=None, score_service=None):
    app()
    return ScoresPage(
        academic_service=AcademicStub(),
        enrollment_service=enrollment_service,
        score_service=score_service,
    )


def test_complete_context_loads_students_for_selected_class_and_year():
    roster = EnrollmentStub()
    page = make_page(roster, ScoreStub())

    complete_context(page)

    assert roster.calls == [(61, 2)]
    assert page.score_table.rowCount() == 2
    assert page.score_table.item(0, 1).text() == "HS01"
    assert page.score_table.item(1, 2).text() == "Học sinh 2"


def test_table_keeps_enrollment_id_for_each_row():
    page = make_page(EnrollmentStub(), ScoreStub())
    complete_context(page)

    assert page.enrollment_id_at_row(0) == 701
    assert page.enrollment_id_at_row(1) == 702
    assert page.score_table.item(0, 0).data(
        Qt.ItemDataRole.UserRole
    ) == 701


def test_save_one_score_sends_enrollment_and_context_assessment():
    scores = ScoreStub()
    page = make_page(EnrollmentStub(), scores)
    complete_context(page)
    page.score_table.item(0, 3).setText("7,25")

    assert page.save_scores() is True
    assert len(scores.calls) == 1
    assert scores.calls[0][0].enrollment_id == 701
    assert scores.calls[0][0].assessment_id == 101
    assert scores.calls[0][0].score_value == Decimal("7.25")


def test_save_multiple_scores_uses_one_batch_call():
    scores = ScoreStub()
    page = make_page(EnrollmentStub(), scores)
    complete_context(page)
    page.score_table.item(0, 3).setText("6")
    page.score_table.item(1, 3).setText("8.5")

    assert page.save_scores() is True
    assert len(scores.calls) == 1
    assert [entry.enrollment_id for entry in scores.calls[0]] == [
        701,
        702,
    ]


def test_incomplete_context_cannot_save():
    scores = ScoreStub()
    page = make_page(EnrollmentStub(), scores)

    assert page.save_button.isEnabled() is False
    assert page.save_scores() is False
    assert scores.calls == []


def test_empty_class_does_not_crash_and_disables_save():
    scores = ScoreStub()
    page = make_page(EnrollmentStub(result=[]), scores)

    complete_context(page)

    assert page.score_table.rowCount() == 0
    assert page.save_button.isEnabled() is False
    assert page.save_scores() is False
    assert scores.calls == []


def test_roster_load_error_is_rendered_without_crash():
    page = make_page(
        EnrollmentStub(error=RuntimeError("roster unavailable")),
        ScoreStub(),
    )

    complete_context(page)

    assert page.score_table.rowCount() == 0
    assert page.save_button.isEnabled() is False
    assert page.context_status_label.text() == "roster unavailable"


def test_successful_rows_cannot_be_created_twice():
    scores = ScoreStub()
    page = make_page(EnrollmentStub(), scores)
    complete_context(page)
    page.score_table.item(0, 3).setText("7")

    assert page.save_scores() is True
    assert page.save_scores() is False
    assert len(scores.calls) == 1
    assert not bool(
        page.score_table.item(0, 3).flags()
        & Qt.ItemFlag.ItemIsEditable
    )


def test_duplicate_create_error_does_not_overwrite_or_lock_input():
    scores = ScoreStub(
        error=DuplicateError("Điểm đã tồn tại.")
    )
    page = make_page(EnrollmentStub(), scores)
    complete_context(page)
    page.score_table.item(0, 3).setText("9")

    assert page.save_scores() is False
    assert page.score_table.item(0, 3).text() == "9"
    assert bool(
        page.score_table.item(0, 3).flags()
        & Qt.ItemFlag.ItemIsEditable
    )
    assert page.context_status_label.text() == "Điểm đã tồn tại."


def test_manual_entry_ui_has_no_sql_support_or_detection_calls():
    source = inspect.getsource(ScoresPage).upper()

    assert "SELECT " not in source
    assert "INSERT " not in source
    assert "SUPPORTSERVICE" not in source
    assert "INTERVENTION" not in source
    assert "CREATE_SCORE_AND_DETECT" not in source
