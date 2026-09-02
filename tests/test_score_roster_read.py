import inspect
import os
from contextlib import contextmanager
from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from exceptions import ValidationError
from models.dto.assessment import Assessment
from models.dto.score import ScoreRosterItem
from models.enums import AssessmentStatus, EnrollmentStatus
from repositories.score_repository import ScoreRepository
from services.score_service import ScoreService
from ui.pages.scores_page import ScoresPage


def app():
    return QApplication.instance() or QApplication([])


def assessment(subject_id=11, school_year_id=2, assessment_id=101):
    return Assessment(
        assessment_id=assessment_id,
        subject_id=subject_id,
        school_year_id=school_year_id,
        assessment_name="Giữa kỳ",
        semester=1,
        assessment_type="MIDTERM",
        assessment_date=date(2026, 10, 1),
        status=AssessmentStatus.ACTIVE,
        created_at=datetime(2026, 9, 1),
    )


def roster_rows(assessment_id=101):
    return [
        ScoreRosterItem(
            701,
            "student-1",
            "HS01",
            "Học sinh 1",
            assessment_id,
            9001 if assessment_id == 101 else None,
            Decimal("8.50") if assessment_id == 101 else None,
        ),
        ScoreRosterItem(
            702,
            "student-2",
            "HS02",
            "Học sinh 2",
            assessment_id,
            None,
            None,
        ),
    ]


class DbStub:
    def __init__(self):
        self.connection = object()
        self.transactions = 0

    @contextmanager
    def transaction(self):
        self.transactions += 1
        yield self.connection


class AcademicRepositoryStub:
    def __init__(self, value):
        self.value = value
        self.calls = []

    def get_assessment_by_id(self, connection, assessment_id):
        self.calls.append((connection, assessment_id))
        return self.value


class ScoreRepositoryStub:
    def __init__(self, result=()):
        self.result = list(result)
        self.calls = []

    def list_by_class_assessment(
        self,
        connection,
        class_id,
        school_year_id,
        assessment_id,
        status,
    ):
        self.calls.append(
            (
                connection,
                class_id,
                school_year_id,
                assessment_id,
                status,
            )
        )
        return self.result


def test_service_reads_context_roster_in_constant_queries():
    db = DbStub()
    academic_repository = AcademicRepositoryStub(assessment())
    score_repository = ScoreRepositoryStub(roster_rows())
    service = ScoreService(
        db,
        score_repository=score_repository,
        academic_repository=academic_repository,
    )

    result = service.list_score_roster(61, 2, 11, 101)

    assert result == roster_rows()
    assert db.transactions == 1
    assert len(academic_repository.calls) == 1
    assert score_repository.calls == [
        (db.connection, 61, 2, 101, EnrollmentStatus.ACTIVE)
    ]


@pytest.mark.parametrize(
    "stored,selected",
    [
        (assessment(subject_id=12), (61, 2, 11, 101)),
        (assessment(school_year_id=3), (61, 2, 11, 101)),
    ],
)
def test_service_rejects_assessment_outside_selected_context(
    stored,
    selected,
):
    db = DbStub()
    score_repository = ScoreRepositoryStub()
    service = ScoreService(
        db,
        score_repository=score_repository,
        academic_repository=AcademicRepositoryStub(stored),
    )

    with pytest.raises(ValidationError):
        service.list_score_roster(*selected)

    assert score_repository.calls == []


@pytest.mark.parametrize("position", range(4))
def test_service_validates_each_context_identifier(position):
    values = [61, 2, 11, 101]
    values[position] = 0
    db = DbStub()
    service = ScoreService(db)

    with pytest.raises(ValidationError):
        service.list_score_roster(*values)

    assert db.transactions == 0


class RepositoryRow:
    def __init__(self, with_score):
        self.enrollment_id = 701 if with_score else 702
        self.student_id = "student-1" if with_score else "student-2"
        self.student_code = "HS01" if with_score else "HS02"
        self.full_name = "Học sinh 1" if with_score else "Học sinh 2"
        self.assessment_id = 101 if with_score else None
        self.score_id = 9001 if with_score else None
        self.score = Decimal("8.50") if with_score else None


class Cursor:
    def __init__(self):
        self.execute_calls = []

    def execute(self, sql, *parameters):
        self.execute_calls.append((sql, parameters))
        return self

    def fetchall(self):
        return [RepositoryRow(True), RepositoryRow(False)]


class Connection:
    def __init__(self):
        self.cursor_value = Cursor()
        self.commit_calls = 0

    def cursor(self):
        return self.cursor_value

    def commit(self):
        self.commit_calls += 1


def test_repository_loads_roster_and_scores_with_one_read_query():
    connection = Connection()

    rows = ScoreRepository().list_by_class_assessment(
        connection,
        61,
        2,
        101,
        EnrollmentStatus.ACTIVE,
    )

    assert len(connection.cursor_value.execute_calls) == 1
    sql, parameters = connection.cursor_value.execute_calls[0]
    upper_sql = sql.upper()
    assert "LEFT JOIN DBO.SCORES" in upper_sql
    assert "SELECT *" not in upper_sql
    assert all(
        keyword not in upper_sql
        for keyword in ("INSERT ", "UPDATE ", "DELETE ")
    )
    assert parameters == (101, 61, 2, "ACTIVE")
    assert rows[0].score_id == 9001
    assert rows[0].score == Decimal("8.50")
    assert rows[1].assessment_id == 101
    assert rows[1].score_id is None
    assert rows[1].score is None
    assert connection.commit_calls == 0


class AcademicUiStub:
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
            assessment(subject_id, school_year_id, 101),
            assessment(subject_id, school_year_id, 102),
        ]


class ScoreReadWriteStub:
    def __init__(self, *, result=None, error=None):
        self.rows = list(result if result is not None else roster_rows())
        self.error = error
        self.read_calls = []
        self.create_calls = []

    def list_score_roster(
        self,
        class_id,
        school_year_id,
        subject_id,
        assessment_id,
    ):
        self.read_calls.append(
            (class_id, school_year_id, subject_id, assessment_id)
        )
        if self.error is not None:
            raise self.error
        return [
            replace(
                row,
                assessment_id=assessment_id,
                score_id=(
                    row.score_id
                    if row.assessment_id == assessment_id
                    else None
                ),
                score=(
                    row.score
                    if row.assessment_id == assessment_id
                    else None
                ),
            )
            for row in self.rows
        ]

    def create_scores(self, entries):
        batch = tuple(entries)
        self.create_calls.append(batch)
        for entry in batch:
            self.rows = [
                replace(
                    row,
                    score_id=9100 + index,
                    score=entry.score_value,
                )
                if row.enrollment_id == entry.enrollment_id
                else row
                for index, row in enumerate(self.rows)
            ]
        return [object() for _entry in batch]


def select_data(combo, value):
    index = combo.findData(value)
    assert index >= 0
    combo.setCurrentIndex(index)


def complete_context(page, assessment_id=101):
    page.initialize_scores()
    select_data(page.grade_combo, 6)
    select_data(page.class_combo, 61)
    select_data(page.subject_combo, 11)
    select_data(page.assessment_combo, assessment_id)


def make_page(service):
    app()
    return ScoresPage(
        academic_service=AcademicUiStub(),
        score_service=service,
    )


def test_page_shows_saved_and_missing_score_states():
    service = ScoreReadWriteStub()
    page = make_page(service)

    complete_context(page)

    assert service.read_calls == [(61, 2, 11, 101)]
    assert page.score_table.item(0, 3).text() == "8.50"
    assert page.score_table.item(0, 4).text() == "Đã có điểm"
    assert page.score_id_at_row(0) == 9001
    assert page.score_table.item(1, 3).text() == ""
    assert page.score_table.item(1, 4).text() == "Chưa có điểm"
    assert page.score_id_at_row(1) is None


def test_existing_score_is_read_only_while_missing_score_is_editable():
    page = make_page(ScoreReadWriteStub())
    complete_context(page)

    assert not bool(
        page.score_table.item(0, 3).flags()
        & Qt.ItemFlag.ItemIsEditable
    )
    assert bool(
        page.score_table.item(1, 3).flags()
        & Qt.ItemFlag.ItemIsEditable
    )


def test_context_change_refreshes_only_selected_assessment():
    service = ScoreReadWriteStub()
    page = make_page(service)
    complete_context(page)

    select_data(page.assessment_combo, 102)

    assert service.read_calls == [
        (61, 2, 11, 101),
        (61, 2, 11, 102),
    ]
    assert all(row.assessment_id == 102 for row in page.score_rows)
    assert all(row.score is None for row in page.score_rows)


def test_successful_create_refreshes_persisted_read_state():
    service = ScoreReadWriteStub()
    page = make_page(service)
    complete_context(page)
    page.score_table.item(1, 3).setText("7.25")

    assert page.save_scores() is True

    assert len(service.create_calls) == 1
    assert len(service.read_calls) == 2
    assert page.score_table.item(1, 3).text() == "7.25"
    assert page.score_table.item(1, 4).text() == "Đã có điểm"
    assert page.score_id_at_row(1) is not None
    assert not bool(
        page.score_table.item(1, 3).flags()
        & Qt.ItemFlag.ItemIsEditable
    )


def test_incomplete_context_clears_score_read_state():
    page = make_page(ScoreReadWriteStub())
    complete_context(page)

    page.subject_combo.setCurrentIndex(0)

    assert page.score_table.rowCount() == 0
    assert page.score_rows == ()
    assert page.save_button.isEnabled() is False


def test_empty_roster_and_read_error_remain_usable():
    empty_page = make_page(ScoreReadWriteStub(result=[]))
    complete_context(empty_page)
    assert empty_page.score_table.rowCount() == 0
    assert empty_page.save_button.isEnabled() is False

    error_page = make_page(
        ScoreReadWriteStub(error=RuntimeError("read failed"))
    )
    complete_context(error_page)
    assert error_page.score_table.rowCount() == 0
    assert error_page.context_status_label.text() == "read failed"


def test_roster_read_path_has_no_support_or_intervention_dependency():
    source = inspect.getsource(ScoreService.list_score_roster).upper()

    assert "SUPPORT" not in source
    assert "INTERVENTION" not in source
    assert "CREATE_SCORE_AND_DETECT" not in source
