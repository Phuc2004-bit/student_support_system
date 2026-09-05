from __future__ import annotations

from contextlib import contextmanager
from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal
import inspect

import pyodbc
import pytest

from config.database import db_settings
from database.connection import DatabaseManager
from exceptions import DatabaseError, ScoreImportError
from models.dto import (
    Assessment,
    EnrollmentListItem,
    ScoreRosterItem,
    Student,
    StudentCreateData,
)
from models.dto.score_import import (
    ScoreImportContext,
    ScoreImportIssue,
    ScoreImportIssueSeverity,
    ScoreImportPreview,
    ScoreImportRow,
    ScoreImportSourceMetadata,
    ScoreImportWorkbook,
)
from models.enums import AssessmentStatus, EnrollmentStatus, StudentStatus
from repositories.enrollment_repository import EnrollmentRepository
from repositories.academic_repository import AcademicRepository
from repositories.score_repository import ScoreRepository
from repositories.student_repository import StudentRepository
from services.score_import_contract import ScoreImportPreviewServiceContract
from services.score_import_preview_service import ScoreImportPreviewService


NOW = datetime(2026, 9, 5)


def context(**changes):
    values = dict(
        school_year_id=2,
        school_year_name="2026-2027",
        class_id=61,
        class_name="6A1",
        subject_id=9,
        subject_name="Khoa học",
        assessment_id=101,
        assessment_name="Giữa kỳ I",
    )
    values.update(changes)
    return ScoreImportContext(**values)


def workbook(*rows):
    return ScoreImportWorkbook(
        "scores.xlsx",
        "Nhập điểm",
        ScoreImportSourceMetadata("wrong", "wrong", "wrong", "wrong"),
        tuple(rows),
    )


def row(number=7, student_id="student-a", name="An Nguyễn", score=Decimal("8"), issues=()):
    return ScoreImportRow(number, student_id, name, score, score, tuple(issues))


def student(student_id="student-a", name="An Nguyễn"):
    return Student(
        student_id, "HS01", name, None, None, None, None, None,
        StudentStatus.ACTIVE, NOW, NOW,
    )


def enrollment(
    student_id="student-a",
    enrollment_id=501,
    class_id=61,
    year_id=2,
    status=EnrollmentStatus.ACTIVE,
):
    return EnrollmentListItem(
        enrollment_id, student_id, "HS01", "An Nguyễn", class_id, "6A1",
        6, year_id, "2026-2027", status,
    )


def roster_item(student_id="student-a", enrollment_id=501, score_id=None):
    return ScoreRosterItem(
        enrollment_id, student_id, "HS01", "An Nguyễn", 101,
        score_id, Decimal("7") if score_id else None,
    )


class FakeDb:
    def __init__(self, error=None):
        self.connection = object()
        self.error = error
        self.transactions = 0

    @contextmanager
    def transaction(self):
        self.transactions += 1
        if self.error:
            raise self.error
        yield self.connection


class AcademicRepo:
    def __init__(self):
        self.year = (2, "2026-2027", None, None, False)
        self.school_class = (61, "6A1", 6, 6, 2, "2026-2027", None, "ACTIVE")
        self.subject = type("Subject", (), {"is_active": True})()
        self.assessment = Assessment(
            101, 9, 2, "Giữa kỳ I", 1, "MIDTERM", date(2026, 10, 1),
            AssessmentStatus.ACTIVE, NOW,
        )
        self.calls = []

    def get_school_year_by_id(self, connection, value):
        self.calls.append(("year", value)); return self.year

    def get_class_by_id(self, connection, value):
        self.calls.append(("class", value)); return self.school_class

    def get_subject_by_id(self, connection, value):
        self.calls.append(("subject", value)); return self.subject

    def get_assessment_by_id(self, connection, value):
        self.calls.append(("assessment", value)); return self.assessment


class StudentRepo:
    def __init__(self, values=None):
        self.values = [student()] if values is None else values
        self.calls = []

    def list_by_ids(self, connection, student_ids):
        self.calls.append(student_ids); return self.values


class EnrollmentRepo:
    def __init__(self, values=None):
        self.values = [enrollment()] if values is None else values
        self.calls = []

    def list_by_student_ids(self, connection, student_ids):
        self.calls.append(student_ids); return self.values


class ScoreRepo:
    def __init__(self, values=None):
        self.values = [roster_item()] if values is None else values
        self.calls = []

    def list_by_class_assessment(self, connection, *args):
        self.calls.append(args); return self.values


def service(*, academic=None, students=None, enrollments=None, scores=None, db=None):
    return ScoreImportPreviewService(
        db or FakeDb(), academic or AcademicRepo(), students or StudentRepo(),
        enrollments or EnrollmentRepo(), scores or ScoreRepo(),
    )


def codes(result, index=0):
    return {issue.code for issue in result.rows[index].issues}


def test_preview_contract_and_happy_path_use_authoritative_context():
    svc = service()
    selected = context()
    source = workbook(row())
    assert isinstance(svc, ScoreImportPreviewServiceContract)
    result = svc.preview_import(selected, source)
    assert isinstance(result, ScoreImportPreview)
    assert result.context is selected
    assert result.rows[0].enrollment_id == 501
    assert result.rows[0].normalized_score == Decimal("8")
    assert result.valid_count == 1
    assert result.invalid_count == 0
    assert result.can_commit is True
    assert source.metadata.school_year_name == "wrong"


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda repo: setattr(repo, "year", None), "năm học"),
        (lambda repo: setattr(repo, "school_class", None), "lớp"),
        (lambda repo: setattr(repo, "school_class", (61, "6A1", 6, 6, 3, "x", None, "ACTIVE")), "Lớp"),
        (lambda repo: setattr(repo, "subject", None), "môn học"),
        (lambda repo: setattr(repo, "subject", type("Subject", (), {"is_active": False})()), "Môn học"),
        (lambda repo: setattr(repo, "assessment", None), "bài đánh giá"),
        (lambda repo: setattr(repo, "assessment", replace(repo.assessment, status=AssessmentStatus.CANCELLED)), "Bài đánh giá"),
        (lambda repo: setattr(repo, "assessment", replace(repo.assessment, school_year_id=3)), "năm học"),
        (lambda repo: setattr(repo, "assessment", replace(repo.assessment, subject_id=10)), "môn học"),
    ],
)
def test_invalid_authoritative_context_is_blocked(mutation, message):
    repository = AcademicRepo()
    mutation(repository)
    with pytest.raises(ScoreImportError, match=message):
        service(academic=repository).preview_import(context(), workbook(row()))


@pytest.mark.parametrize("field", ["school_year_id", "class_id", "subject_id", "assessment_id"])
def test_invalid_context_identifier_is_blocked_before_database(field):
    db = FakeDb()
    with pytest.raises(ScoreImportError):
        service(db=db).preview_import(context(**{field: 0}), workbook(row()))
    assert db.transactions == 0


def test_student_name_is_informational_warning_and_not_identity():
    result = service().preview_import(context(), workbook(row(name="Tên Excel khác")))
    assert result.rows[0].student_name_db == "An Nguyễn"
    assert result.rows[0].is_valid is True
    assert codes(result) == {"STUDENT_NAME_MISMATCH"}
    assert result.rows[0].issues[0].severity == ScoreImportIssueSeverity.WARNING


@pytest.mark.parametrize(
    ("students", "enrollments", "expected"),
    [
        ([], [], "UNKNOWN_STUDENT"),
        ([student()], [], "MISSING_ENROLLMENT"),
        ([student()], [enrollment(year_id=3)], "ENROLLMENT_WRONG_YEAR"),
        ([student()], [enrollment(class_id=62)], "ENROLLMENT_WRONG_CLASS"),
        ([student()], [enrollment(status=EnrollmentStatus.TRANSFERRED)], "ENROLLMENT_NOT_ACTIVE"),
    ],
)
def test_student_and_enrollment_resolution_failures(students, enrollments, expected):
    result = service(
        students=StudentRepo(students), enrollments=EnrollmentRepo(enrollments),
        scores=ScoreRepo([]),
    ).preview_import(context(), workbook(row()))
    assert expected in codes(result)
    assert result.rows[0].enrollment_id is None
    assert result.can_commit is False


@pytest.mark.parametrize("value", [Decimal("0"), Decimal("10"), Decimal("7.25")])
def test_canonical_score_boundaries_and_decimal_are_valid(value):
    result = service().preview_import(context(), workbook(row(score=value)))
    assert result.rows[0].normalized_score == value
    assert result.rows[0].is_valid


@pytest.mark.parametrize(
    "value", [None, True, Decimal("-0.01"), Decimal("10.01"), Decimal("1.001"), Decimal("NaN"), Decimal("Infinity")]
)
def test_canonical_score_policy_blocks_invalid_and_blank_values(value):
    result = service().preview_import(context(), workbook(row(score=value)))
    assert "INVALID_SCORE" in codes(result)
    assert result.rows[0].normalized_score is None
    assert not result.rows[0].is_valid


def test_parser_issues_are_preserved_without_duplicate_score_issue():
    parser_issue = ScoreImportIssue("BOOLEAN_SCORE", "score", "invalid")
    source_row = ScoreImportRow(12, "student-a", "An Nguyễn", True, None, (parser_issue,))
    result = service().preview_import(context(), workbook(source_row))
    assert result.rows[0].row_number == 12
    assert result.rows[0].issues[0] is parser_issue
    assert [issue.code for issue in result.rows[0].issues].count("INVALID_SCORE") == 0


def test_duplicate_file_marks_every_occurrence_and_never_last_row_wins():
    result = service().preview_import(
        context(), workbook(row(7, score=Decimal("6")), row(11, score=Decimal("9")))
    )
    assert [item.row_number for item in result.rows] == [7, 11]
    assert all("DUPLICATE_FILE_ROW" in codes(result, i) for i in range(2))
    assert result.invalid_count == 2
    assert result.can_commit is False


def test_existing_database_score_is_duplicate_and_never_mutated():
    existing = roster_item(score_id=900)
    repository = ScoreRepo([existing])
    result = service(scores=repository).preview_import(context(), workbook(row()))
    assert "DUPLICATE_DATABASE_SCORE" in codes(result)
    assert repository.values == [existing]
    assert not hasattr(repository, "update")


def test_warning_does_not_block_but_empty_or_error_preview_cannot_commit():
    warning = service().preview_import(context(), workbook(row(name="other")))
    empty = service(
        students=StudentRepo([]), enrollments=EnrollmentRepo([]), scores=ScoreRepo([])
    ).preview_import(context(), workbook())
    error = service().preview_import(context(), workbook(row(score=None)))
    assert warning.can_commit is True
    assert empty.can_commit is False
    assert error.can_commit is False


def test_batch_reads_once_and_workbook_is_not_mutated_for_many_rows():
    students = StudentRepo([student("student-a"), student("student-b", "Bình")])
    enrollments = EnrollmentRepo([
        enrollment("student-a", 501), enrollment("student-b", 502),
    ])
    scores = ScoreRepo([
        roster_item("student-a", 501), roster_item("student-b", 502),
    ])
    source = workbook(row(7), row(8, "student-b", "Bình", Decimal("9")))
    original_rows = source.rows
    result = service(students=students, enrollments=enrollments, scores=scores).preview_import(context(), source)
    assert result.valid_count == 2
    assert students.calls == [("student-a", "student-b")]
    assert enrollments.calls == [("student-a", "student-b")]
    assert len(scores.calls) == 1
    assert source.rows is original_rows


def test_database_driver_error_is_normalized():
    with pytest.raises(DatabaseError) as exc_info:
        service(db=FakeDb(pyodbc.Error("raw driver detail"))).preview_import(
            context(), workbook(row())
        )
    assert "raw driver detail" not in str(exc_info.value)


def test_preview_service_is_read_only_and_has_no_support_dependency():
    source = inspect.getsource(inspect.getmodule(ScoreImportPreviewService)).upper()
    for forbidden in (
        "SUPPORTSERVICE", "INSERT INTO", "UPDATE DBO", "DELETE FROM",
        ".COMMIT(", "CREATE_SCORE(", "CREATE_INTERVENTION",
    ):
        assert forbidden not in source


def test_batch_repository_methods_are_parameterized_and_do_not_commit():
    source = (
        inspect.getsource(StudentRepository.list_by_ids)
        + inspect.getsource(EnrollmentRepository.list_by_student_ids)
    ).upper()
    assert "SELECT *" not in source
    assert ".COMMIT(" not in source
    assert "?" in source


TEST_YEAR = "T132_2627"
TEST_CLASS = "T132_6A"
TEST_SUBJECT = "T132_M1"
TEST_STUDENT_ID = "t132-student-1"
TEST_STUDENT_CODE = "T13201"


def get_test_db():
    connection_string = db_settings.connection_string().replace(
        "DATABASE=student_support_db;", "DATABASE=student_support_db_test;"
    )
    assert "student_support_db_test" in connection_string
    return DatabaseManager(connection_string)


def cleanup_integration(db):
    with db.transaction() as connection:
        cursor = connection.cursor()
        cursor.execute(
            "DELETE FROM dbo.SCORES WHERE enrollment_id IN "
            "(SELECT enrollment_id FROM dbo.STUDENT_ENROLLMENTS WHERE student_id = ?)",
            TEST_STUDENT_ID,
        )
        cursor.execute(
            "DELETE FROM dbo.STUDENT_ENROLLMENTS WHERE student_id = ?",
            TEST_STUDENT_ID,
        )
        cursor.execute("DELETE FROM dbo.STUDENTS WHERE student_id = ?", TEST_STUDENT_ID)
        cursor.execute(
            "DELETE FROM dbo.ASSESSMENTS WHERE subject_id IN "
            "(SELECT subject_id FROM dbo.SUBJECTS WHERE subject_code = ?)",
            TEST_SUBJECT,
        )
        cursor.execute("DELETE FROM dbo.SUBJECTS WHERE subject_code = ?", TEST_SUBJECT)
        cursor.execute("DELETE FROM dbo.CLASSES WHERE class_name = ?", TEST_CLASS)
        cursor.execute("DELETE FROM dbo.SCHOOL_YEARS WHERE year_name = ?", TEST_YEAR)


def test_preview_integration_reads_real_context_roster_and_duplicate_without_writes():
    db = get_test_db()
    academic = AcademicRepository()
    students = StudentRepository()
    enrollments = EnrollmentRepository()
    scores = ScoreRepository()
    cleanup_integration(db)
    try:
        with db.transaction() as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT grade_id FROM dbo.GRADES WHERE grade_number = ?", 6)
            grade = cursor.fetchone()
            if grade is None:
                cursor.execute(
                    "INSERT INTO dbo.GRADES (grade_number, grade_name) "
                    "OUTPUT INSERTED.grade_id VALUES (?, ?)",
                    6, "Khối 6",
                )
                grade_id = cursor.fetchone()[0]
            else:
                grade_id = grade[0]
            year_id = academic.create_school_year(
                connection, TEST_YEAR, date(2026, 9, 1), date(2027, 5, 31), False
            )
            class_id = academic.create_class(
                connection, TEST_CLASS, grade_id, year_id
            )
            subject_id = academic.create_subject(
                connection, TEST_SUBJECT, "Môn T132"
            )
            assessment = academic.create_assessment(
                connection, subject_id, year_id, "T132_A1", 1, "TEST",
                date(2026, 10, 1),
            )
            students.create(
                connection, TEST_STUDENT_ID,
                StudentCreateData(TEST_STUDENT_CODE, "Học sinh T132"),
            )
            saved_enrollment = enrollments.create(
                connection, TEST_STUDENT_ID, class_id, date(2026, 9, 1)
            )

        selected = ScoreImportContext(
            year_id, TEST_YEAR, class_id, TEST_CLASS, subject_id, "Môn T132",
            assessment.assessment_id, "T132_A1",
        )
        source = workbook(row(7, TEST_STUDENT_ID, "Học sinh T132", Decimal("8.25")))
        preview_service = ScoreImportPreviewService(db)
        valid = preview_service.preview_import(selected, source)
        assert valid.can_commit is True
        assert valid.rows[0].enrollment_id == saved_enrollment.enrollment_id

        with db.transaction() as connection:
            scores.create(
                connection, saved_enrollment.enrollment_id,
                assessment.assessment_id, Decimal("7.00"),
            )
            before = connection.cursor().execute(
                "SELECT COUNT(*) FROM dbo.SCORES WHERE enrollment_id = ?",
                saved_enrollment.enrollment_id,
            ).fetchone()[0]

        duplicate = preview_service.preview_import(selected, source)
        assert "DUPLICATE_DATABASE_SCORE" in codes(duplicate)
        assert duplicate.can_commit is False
        with db.transaction() as connection:
            after = connection.cursor().execute(
                "SELECT COUNT(*) FROM dbo.SCORES WHERE enrollment_id = ?",
                saved_enrollment.enrollment_id,
            ).fetchone()[0]
            support_count = connection.cursor().execute(
                "SELECT COUNT(*) FROM dbo.INTERVENTIONS WHERE enrollment_id = ?",
                saved_enrollment.enrollment_id,
            ).fetchone()[0]
        assert after == before == 1
        assert support_count == 0
    finally:
        cleanup_integration(db)
