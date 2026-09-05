from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
import inspect

import pytest

from config.database import db_settings
from database.connection import DatabaseManager
from exceptions import DatabaseError, DuplicateError, MissingSupportRuleError, ScoreImportError
from models.dto import Score, ScoreBatchDetectionResult, StudentCreateData
from models.dto.score_import import (
    ScoreImportContext,
    ScoreImportIssue,
    ScoreImportPreview,
    ScoreImportPreviewRow,
    ScoreImportRow,
    ScoreImportSourceMetadata,
    ScoreImportTransactionResult,
    ScoreImportWorkbook,
)
from models.enums import AssessmentStatus, EnrollmentStatus, InterventionStatus
from repositories import (
    AcademicRepository,
    EnrollmentRepository,
    InterventionRepository,
    ScoreRepository,
    StudentRepository,
    SupportRuleRepository,
)
from services.score_import_commit_service import ScoreImportCommitService
from services.score_import_contract import ScoreImportCommitServiceContract
from services.score_import_preview_service import ScoreImportPreviewService
from services.score_service import ScoreService


NOW = datetime(2026, 9, 6)


def context(**changes):
    values = dict(
        school_year_id=2, school_year_name="2026-2027",
        class_id=61, class_name="6A1", subject_id=9,
        subject_name="Khoa học", assessment_id=101,
        assessment_name="Giữa kỳ I",
    )
    values.update(changes)
    return ScoreImportContext(**values)


def preview(*rows, selected=None):
    return ScoreImportPreview(selected or context(), tuple(rows))


def preview_row(number=7, enrollment_id=501, score=Decimal("8"), issues=()):
    return ScoreImportPreviewRow(
        number, f"student-{enrollment_id}", "Name", "Name",
        enrollment_id, score, tuple(issues),
    )


class AtomicDb:
    def __init__(self, resources=()):
        self.connection = object()
        self.resources = list(resources)
        self.transactions = self.commits = self.rollbacks = 0

    @contextmanager
    def transaction(self):
        self.transactions += 1
        snapshots = [list(resource) for resource in self.resources]
        try:
            yield self.connection
        except Exception:
            for resource, snapshot in zip(self.resources, snapshots):
                resource[:] = snapshot
            self.rollbacks += 1
            raise
        else:
            self.commits += 1


class Revalidator:
    def __init__(self, error=None):
        self.error = error
        self.calls = []

    def _revalidate_preview(self, connection, value):
        self.calls.append((connection, value))
        if self.error:
            raise self.error
        return value


class BatchWriter:
    def __init__(self, scores, interventions, fail_at=None, error=None):
        self.scores = scores
        self.interventions = interventions
        self.fail_at = fail_at
        self.error = error
        self.create_intervention_at = None
        self.calls = []

    def _create_scores_and_detect(self, connection, entries):
        self.calls.append((connection, entries))
        created = []
        for index, entry in enumerate(entries, start=1):
            if self.fail_at == index:
                raise self.error or RuntimeError("repository failure")
            item = Score(
                100 + index, entry.enrollment_id, entry.assessment_id,
                entry.score_value, NOW, NOW,
            )
            self.scores.append(item)
            created.append(item)
            if self.create_intervention_at == index:
                self.interventions.append(object())
        return ScoreBatchDetectionResult(tuple(created), tuple(self.interventions))


def make_unit_service(*, revalidation_error=None, fail_at=None, error=None, interventions=()):
    saved_scores = []
    saved_interventions = list(interventions)
    db = AtomicDb((saved_scores, saved_interventions))
    revalidator = Revalidator(revalidation_error)
    writer = BatchWriter(saved_scores, saved_interventions, fail_at, error)
    service = ScoreImportCommitService(db, revalidator, writer)
    return service, db, revalidator, writer, saved_scores, saved_interventions


def test_contract_and_valid_preview_commit_all_rows_once():
    service, db, revalidator, writer, scores, _ = make_unit_service()
    source = preview(preview_row(7, 501, Decimal("0")), preview_row(8, 502, Decimal("10")))
    assert isinstance(service, ScoreImportCommitServiceContract)
    result = service.commit_import(source)
    assert isinstance(result, ScoreImportTransactionResult)
    assert result.success is True
    assert result.assessment_id == 101
    assert result.imported_count == 2
    assert result.score_ids == (101, 102)
    assert [(x.enrollment_id, x.assessment_id, x.score) for x in scores] == [
        (501, 101, Decimal("0")), (502, 101, Decimal("10")),
    ]
    assert db.transactions == db.commits == 1
    assert db.rollbacks == 0
    assert revalidator.calls == [(db.connection, source)]
    assert len(writer.calls) == 1


@pytest.mark.parametrize(
    "source",
    [
        preview(),
        preview(preview_row(issues=(ScoreImportIssue("INVALID", "score", "bad"),))),
        None,
    ],
)
def test_invalid_or_empty_preview_is_blocked_before_transaction(source):
    service, db, _revalidator, writer, scores, _ = make_unit_service()
    with pytest.raises(ScoreImportError):
        service.commit_import(source)
    assert db.transactions == 0
    assert writer.calls == []
    assert scores == []


@pytest.mark.parametrize("enrollment_id,score", [(None, Decimal("8")), (501, None)])
def test_tampered_preview_fields_are_not_silently_skipped(enrollment_id, score):
    service, db, *_ = make_unit_service()
    with pytest.raises(ScoreImportError):
        service.commit_import(preview(preview_row(enrollment_id=enrollment_id, score=score)))
    assert db.transactions == 0


def test_stale_preview_is_revalidated_inside_owned_transaction():
    service, db, _revalidator, writer, scores, _ = make_unit_service(
        revalidation_error=ScoreImportError("stale")
    )
    with pytest.raises(ScoreImportError, match="stale"):
        service.commit_import(preview(preview_row()))
    assert db.transactions == 1
    assert db.rollbacks == 1
    assert writer.calls == []
    assert scores == []


def test_repository_failure_mid_batch_rolls_back_and_is_normalized():
    service, db, _revalidator, _writer, scores, _ = make_unit_service(fail_at=2)
    with pytest.raises(DatabaseError) as exc_info:
        service.commit_import(preview(preview_row(7, 501), preview_row(8, 502)))
    assert "repository failure" not in str(exc_info.value)
    assert db.rollbacks == 1
    assert scores == []


def test_duplicate_race_rolls_back_without_normalizing_business_error():
    service, db, _revalidator, _writer, scores, _ = make_unit_service(
        fail_at=2, error=DuplicateError("duplicate")
    )
    with pytest.raises(DuplicateError):
        service.commit_import(preview(preview_row(7, 501), preview_row(8, 502)))
    assert db.rollbacks == 1
    assert scores == []


def test_detection_failure_rolls_back_scores_and_interventions():
    interventions = []
    service, db, _revalidator, writer, scores, saved_interventions = make_unit_service(
        fail_at=3, error=MissingSupportRuleError("missing"),
        interventions=interventions,
    )
    writer.create_intervention_at = 1
    with pytest.raises(MissingSupportRuleError):
        service.commit_import(preview(preview_row(7, 501), preview_row(8, 502), preview_row(9, 503)))
    assert db.rollbacks == 1
    assert scores == []
    assert saved_interventions == []


def test_commit_service_has_no_ui_sql_or_separate_public_service_transaction_calls():
    source = inspect.getsource(inspect.getmodule(ScoreImportCommitService)).upper()
    for forbidden in (
        "PYQT", "SELECT ", "INSERT ", "UPDATE ", "DELETE ",
        ".CREATE_SCORES_AND_DETECT(", ".DETECT_FROM_SCORE(", ".COMMIT(",
    ):
        assert forbidden not in source


T_YEAR = "T133_2627"
T_CLASS = "T133_6A"
T_SUBJECT = "T133_M1"
T_NO_RULE = "T133_M2"
T_STUDENTS = tuple(f"t133-student-{i}" for i in range(1, 4))
T_CODES = tuple(f"T1330{i}" for i in range(1, 4))


def get_test_db():
    connection_string = db_settings.connection_string().replace(
        "DATABASE=student_support_db;", "DATABASE=student_support_db_test;"
    )
    assert "student_support_db_test" in connection_string
    db = DatabaseManager(connection_string)
    with db.transaction() as connection:
        name = connection.cursor().execute("SELECT DB_NAME()").fetchone()[0]
    assert name == "student_support_db_test"
    return db


def cleanup(db):
    with db.transaction() as connection:
        cursor = connection.cursor()
        placeholders = ", ".join("?" for _ in T_STUDENTS)
        cursor.execute(
            f"DELETE FROM dbo.INTERVENTION_REVIEWS WHERE intervention_id IN "
            f"(SELECT intervention_id FROM dbo.INTERVENTIONS WHERE enrollment_id IN "
            f"(SELECT enrollment_id FROM dbo.STUDENT_ENROLLMENTS WHERE student_id IN ({placeholders})))",
            *T_STUDENTS,
        )
        cursor.execute(
            f"DELETE FROM dbo.INTERVENTIONS WHERE enrollment_id IN "
            f"(SELECT enrollment_id FROM dbo.STUDENT_ENROLLMENTS WHERE student_id IN ({placeholders}))",
            *T_STUDENTS,
        )
        cursor.execute(
            f"DELETE FROM dbo.SCORES WHERE enrollment_id IN "
            f"(SELECT enrollment_id FROM dbo.STUDENT_ENROLLMENTS WHERE student_id IN ({placeholders}))",
            *T_STUDENTS,
        )
        cursor.execute(
            "DELETE FROM dbo.SUPPORT_RULES WHERE subject_id IN "
            "(SELECT subject_id FROM dbo.SUBJECTS WHERE subject_code IN (?, ?))",
            T_SUBJECT, T_NO_RULE,
        )
        cursor.execute(
            "DELETE FROM dbo.ASSESSMENTS WHERE subject_id IN "
            "(SELECT subject_id FROM dbo.SUBJECTS WHERE subject_code IN (?, ?))",
            T_SUBJECT, T_NO_RULE,
        )
        cursor.execute(
            f"DELETE FROM dbo.STUDENT_ENROLLMENTS WHERE student_id IN ({placeholders})",
            *T_STUDENTS,
        )
        cursor.execute(
            f"DELETE FROM dbo.STUDENTS WHERE student_id IN ({placeholders})",
            *T_STUDENTS,
        )
        cursor.execute("DELETE FROM dbo.CLASSES WHERE class_name = ?", T_CLASS)
        cursor.execute("DELETE FROM dbo.SUBJECTS WHERE subject_code IN (?, ?)", T_SUBJECT, T_NO_RULE)
        cursor.execute("DELETE FROM dbo.SCHOOL_YEARS WHERE year_name = ?", T_YEAR)


def seed(db):
    academic = AcademicRepository()
    students = StudentRepository()
    enrollments = EnrollmentRepository()
    rules = SupportRuleRepository()
    with db.transaction() as connection:
        cursor = connection.cursor()
        cursor.execute("SELECT grade_id FROM dbo.GRADES WHERE grade_number = ?", 6)
        grade = cursor.fetchone()
        if grade is None:
            cursor.execute(
                "INSERT INTO dbo.GRADES (grade_number, grade_name) "
                "OUTPUT INSERTED.grade_id VALUES (?, ?)", 6, "Khối 6",
            )
            grade_id = cursor.fetchone()[0]
        else:
            grade_id = grade[0]
        year_id = academic.create_school_year(
            connection, T_YEAR, date(2026, 9, 1), date(2027, 5, 31), False
        )
        class_id = academic.create_class(connection, T_CLASS, grade_id, year_id)
        subject_id = academic.create_subject(connection, T_SUBJECT, "Môn T133")
        no_rule_subject_id = academic.create_subject(connection, T_NO_RULE, "Môn NR133")
        assessments = [
            academic.create_assessment(
                connection, subject_id, year_id, f"T133_A{i}", 1, "TEST",
                date(2026, 10, i),
            )
            for i in range(1, 4)
        ]
        no_rule_assessment = academic.create_assessment(
            connection, no_rule_subject_id, year_id, "T133_NR", 1, "TEST",
            date(2026, 11, 1),
        )
        rule = rules.create(connection, subject_id, year_id, Decimal("6.25"))
        enrollment_ids = []
        for student_id, code in zip(T_STUDENTS, T_CODES):
            students.create(
                connection, student_id,
                StudentCreateData(code, f"Học sinh {code}"),
            )
            enrollment_ids.append(
                enrollments.create(
                    connection, student_id, class_id, date(2026, 9, 1)
                ).enrollment_id
            )
    return dict(
        year_id=year_id, class_id=class_id, subject_id=subject_id,
        no_rule_subject_id=no_rule_subject_id, assessments=assessments,
        no_rule_assessment=no_rule_assessment, rule=rule,
        enrollment_ids=tuple(enrollment_ids),
    )


def make_context(data, assessment, subject_id=None, subject_name="Môn T133"):
    return ScoreImportContext(
        data["year_id"], T_YEAR, data["class_id"], T_CLASS,
        subject_id or data["subject_id"], subject_name,
        assessment.assessment_id, assessment.assessment_name,
    )


def make_workbook(values):
    return ScoreImportWorkbook(
        "scores.xlsx", "Nhập điểm", ScoreImportSourceMetadata(),
        tuple(
            ScoreImportRow(
                7 + index, T_STUDENTS[index], f"Học sinh {T_CODES[index]}",
                value, Decimal(value), (),
            )
            for index, value in enumerate(values)
        ),
    )


def count_rows(db, table, assessment_id=None):
    with db.transaction() as connection:
        if assessment_id is None:
            return connection.cursor().execute(
                f"SELECT COUNT(*) FROM dbo.{table} WHERE enrollment_id IN (?, ?, ?)",
                *data_enrollments(db),
            ).fetchone()[0]
        return connection.cursor().execute(
            f"SELECT COUNT(*) FROM dbo.{table} WHERE assessment_id = ?",
            assessment_id,
        ).fetchone()[0]


def data_enrollments(db):
    with db.transaction() as connection:
        placeholders = ", ".join("?" for _ in T_STUDENTS)
        return tuple(
            row[0] for row in connection.cursor().execute(
                f"SELECT enrollment_id FROM dbo.STUDENT_ENROLLMENTS "
                f"WHERE student_id IN ({placeholders}) ORDER BY student_id",
                *T_STUDENTS,
            ).fetchall()
        )


def build_preview(db, selected, values):
    return ScoreImportPreviewService(db).preview_import(
        selected, make_workbook(values)
    )


def test_real_commit_threshold_detection_result_and_trigger_immutability():
    db = get_test_db(); cleanup(db)
    try:
        data = seed(db)
        selected = make_context(data, data["assessments"][0])
        source = build_preview(db, selected, ("6.24", "6.25", "9.00"))
        result = ScoreImportCommitService(db).commit_import(source)
        assert result.imported_count == 3
        assert result.intervention_created_count == 1
        assert len(result.score_ids) == 3
        assert len(result.intervention_ids) == 1
        with db.transaction() as connection:
            saved = ScoreRepository().list_by_class_assessment(
                connection, data["class_id"], data["year_id"],
                data["assessments"][0].assessment_id, EnrollmentStatus.ACTIVE,
            )
            interventions = [
                InterventionRepository().get_by_id(connection, value)
                for value in result.intervention_ids
            ]
            review_count = connection.cursor().execute(
                "SELECT COUNT(*) FROM dbo.INTERVENTION_REVIEWS WHERE intervention_id = ?",
                result.intervention_ids[0],
            ).fetchone()[0]
        assert [item.score for item in saved] == [Decimal("6.24"), Decimal("6.25"), Decimal("9.00")]
        assert interventions[0].status == InterventionStatus.DETECTED
        assert interventions[0].trigger_score_id == saved[0].score_id
        assert ScoreService(db).can_edit_score(saved[0].score_id) is False
        assert ScoreService(db).can_edit_score(saved[1].score_id) is True
        assert review_count == 0
    finally:
        cleanup(db)


def test_real_duplicate_created_after_preview_blocks_whole_import():
    db = get_test_db(); cleanup(db)
    try:
        data = seed(db)
        assessment = data["assessments"][1]
        selected = make_context(data, assessment)
        source = build_preview(db, selected, ("8", "8", "8"))
        with db.transaction() as connection:
            ScoreRepository().create(
                connection, data["enrollment_ids"][1], assessment.assessment_id,
                Decimal("7"),
            )
        with pytest.raises(ScoreImportError):
            ScoreImportCommitService(db).commit_import(source)
        assert count_rows(db, "SCORES", assessment.assessment_id) == 1
    finally:
        cleanup(db)


def test_real_cancelled_assessment_after_preview_is_blocked_without_scores():
    db = get_test_db(); cleanup(db)
    try:
        data = seed(db)
        assessment = data["assessments"][1]
        source = build_preview(db, make_context(data, assessment), ("8", "8", "8"))
        with db.transaction() as connection:
            AcademicRepository().update_assessment(
                connection, assessment.assessment_id, assessment.subject_id,
                assessment.school_year_id, assessment.assessment_name,
                assessment.semester, assessment.assessment_type,
                assessment.assessment_date, AssessmentStatus.CANCELLED,
            )
        with pytest.raises(ScoreImportError):
            ScoreImportCommitService(db).commit_import(source)
        assert count_rows(db, "SCORES", assessment.assessment_id) == 0
    finally:
        cleanup(db)


def test_real_missing_support_rule_rolls_back_all_scores_and_interventions():
    db = get_test_db(); cleanup(db)
    try:
        data = seed(db)
        assessment = data["no_rule_assessment"]
        selected = make_context(
            data, assessment, data["no_rule_subject_id"], "Môn NR133"
        )
        source = build_preview(db, selected, ("2", "8", "9"))
        with pytest.raises(MissingSupportRuleError):
            ScoreImportCommitService(db).commit_import(source)
        assert count_rows(db, "SCORES", assessment.assessment_id) == 0
        with db.transaction() as connection:
            interventions = connection.cursor().execute(
                "SELECT COUNT(*) FROM dbo.INTERVENTIONS WHERE enrollment_id IN (?, ?, ?)",
                *data["enrollment_ids"],
            ).fetchone()[0]
        assert interventions == 0
    finally:
        cleanup(db)


def test_real_open_intervention_is_reused_without_counting_as_new():
    db = get_test_db(); cleanup(db)
    try:
        data = seed(db)
        first = data["assessments"][0]
        second = data["assessments"][1]
        first_preview = build_preview(db, make_context(data, first), ("2", "8", "9"))
        first_result = ScoreImportCommitService(db).commit_import(first_preview)
        second_preview = ScoreImportPreviewService(db).preview_import(
            make_context(data, second),
            ScoreImportWorkbook(
                "one.xlsx", "Nhập điểm", ScoreImportSourceMetadata(),
                (ScoreImportRow(7, T_STUDENTS[0], f"Học sinh {T_CODES[0]}", "2", Decimal("2"), ()),),
            ),
        )
        second_result = ScoreImportCommitService(db).commit_import(second_preview)
        assert first_result.intervention_created_count == 1
        assert second_result.intervention_created_count == 0
        with db.transaction() as connection:
            count = connection.cursor().execute(
                "SELECT COUNT(*) FROM dbo.INTERVENTIONS WHERE enrollment_id = ? AND subject_id = ?",
                data["enrollment_ids"][0], data["subject_id"],
            ).fetchone()[0]
        assert count == 1
    finally:
        cleanup(db)
