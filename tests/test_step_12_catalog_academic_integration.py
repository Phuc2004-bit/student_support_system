from datetime import date
from decimal import Decimal

import pytest

from config.database import db_settings
from database.connection import DatabaseManager
from exceptions import BusinessRuleError, DuplicateError, ValidationError
from models.dto import StudentCreateData
from models.enums import AssessmentStatus, InterventionStatus
from repositories import (
    EnrollmentRepository,
    InterventionRepository,
    ScoreRepository,
    StudentRepository,
)
from services import AcademicService, SupportService


YEAR = "T126_2038_2039"
CLASS_NAME = "T126_10A"
SUBJECT_A_CODE = "T126_SUB_A"
SUBJECT_B_CODE = "T126_SUB_B"
ASSESSMENT_LOW = "T126_LOW"
ASSESSMENT_EXACT = "T126_EXACT"
STUDENT_ID = "T126-STUDENT-001"
STUDENT_CODE = "T126S01"


def require_test_database(connection_string: str) -> str:
    normalized = connection_string.upper().replace(" ", "")
    if "DATABASE=STUDENT_SUPPORT_DB_TEST;" not in normalized:
        raise RuntimeError("Integration writes require student_support_db_test.")
    return connection_string


def get_test_db() -> DatabaseManager:
    connection_string = db_settings.connection_string().replace(
        "DATABASE=student_support_db;",
        "DATABASE=student_support_db_test;",
    )
    return DatabaseManager(require_test_database(connection_string))


def assert_connected_test_database(db: DatabaseManager) -> None:
    connection = db.get_connection()
    try:
        database_name = connection.cursor().execute("SELECT DB_NAME()").fetchone()[0]
        assert database_name == "student_support_db_test"
    finally:
        connection.rollback()
        connection.close()


def cleanup(db: DatabaseManager) -> None:
    require_test_database(db.connection_string)
    assert_connected_test_database(db)
    with db.transaction() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            DELETE FROM dbo.INTERVENTION_REVIEWS
            WHERE intervention_id IN
            (
                SELECT intervention_id FROM dbo.INTERVENTIONS
                WHERE enrollment_id IN
                (
                    SELECT enrollment_id FROM dbo.STUDENT_ENROLLMENTS
                    WHERE student_id = ?
                )
            )
            """,
            STUDENT_ID,
        )
        cursor.execute(
            """
            DELETE FROM dbo.INTERVENTIONS
            WHERE enrollment_id IN
            (
                SELECT enrollment_id FROM dbo.STUDENT_ENROLLMENTS
                WHERE student_id = ?
            )
            """,
            STUDENT_ID,
        )
        cursor.execute(
            """
            DELETE FROM dbo.SCORES
            WHERE enrollment_id IN
            (
                SELECT enrollment_id FROM dbo.STUDENT_ENROLLMENTS
                WHERE student_id = ?
            )
            """,
            STUDENT_ID,
        )
        cursor.execute(
            """
            DELETE FROM dbo.SUPPORT_RULES
            WHERE subject_id IN
            (
                SELECT subject_id FROM dbo.SUBJECTS
                WHERE subject_code IN (?, ?)
            )
            """,
            SUBJECT_A_CODE,
            SUBJECT_B_CODE,
        )
        cursor.execute(
            """
            DELETE FROM dbo.ASSESSMENTS
            WHERE subject_id IN
            (
                SELECT subject_id FROM dbo.SUBJECTS
                WHERE subject_code IN (?, ?)
            )
            """,
            SUBJECT_A_CODE,
            SUBJECT_B_CODE,
        )
        cursor.execute(
            "DELETE FROM dbo.STUDENT_ENROLLMENTS WHERE student_id = ?",
            STUDENT_ID,
        )
        cursor.execute(
            "DELETE FROM dbo.STUDENTS WHERE student_id = ? OR student_code = ?",
            STUDENT_ID,
            STUDENT_CODE,
        )
        cursor.execute(
            "DELETE FROM dbo.CLASSES WHERE class_name = ?",
            CLASS_NAME,
        )
        cursor.execute(
            "DELETE FROM dbo.SUBJECTS WHERE subject_code IN (?, ?)",
            SUBJECT_A_CODE,
            SUBJECT_B_CODE,
        )
        cursor.execute(
            "DELETE FROM dbo.SCHOOL_YEARS WHERE year_name = ?",
            YEAR,
        )


def test_test_database_guard_rejects_production_connection_before_write():
    with pytest.raises(RuntimeError):
        require_test_database(
            "SERVER=.\\SQLEXPRESS;DATABASE=student_support_db;Trusted_Connection=yes;"
        )


def test_subject_assessment_rule_and_detection_history_against_test_database():
    db = get_test_db()
    assert_connected_test_database(db)
    cleanup(db)
    academic = AcademicService(db)
    student_repository = StudentRepository()
    enrollment_repository = EnrollmentRepository()
    score_repository = ScoreRepository()
    intervention_repository = InterventionRepository()

    try:
        year_id = academic.create_school_year(
            YEAR,
            date(2038, 9, 1),
            date(2039, 5, 31),
            False,
        )
        subject_a_id = academic.create_subject(
            SUBJECT_A_CODE,
            "Catalog subject A",
        )
        subject_b_id = academic.create_subject(
            SUBJECT_B_CODE,
            "Catalog subject B",
        )
        with pytest.raises(DuplicateError):
            academic.create_subject(SUBJECT_A_CODE.lower(), "Duplicate")

        low_assessment = academic.create_assessment(
            subject_a_id,
            year_id,
            ASSESSMENT_LOW,
            1,
            "QUIZ",
            date(2038, 10, 1),
        )
        exact_assessment = academic.create_assessment(
            subject_a_id,
            year_id,
            ASSESSMENT_EXACT,
            1,
            "QUIZ",
            date(2038, 10, 2),
        )
        with pytest.raises(DuplicateError):
            academic.create_assessment(
                subject_a_id, year_id, ASSESSMENT_LOW, 2, "FINAL", None
            )
        with pytest.raises(ValidationError):
            academic.create_assessment(999999, year_id, "Invalid", 1, None, None)

        with db.transaction() as connection:
            grade_row = connection.cursor().execute(
                "SELECT grade_id FROM dbo.GRADES WHERE grade_number = ?",
                10,
            ).fetchone()
            assert grade_row is not None
            grade_id = int(grade_row[0])

        class_id = academic.create_class(CLASS_NAME, grade_id, year_id)
        with db.transaction() as connection:
            student_repository.create(
                connection,
                STUDENT_ID,
                StudentCreateData(STUDENT_CODE, "Student 126"),
            )
            enrollment = enrollment_repository.create(
                connection,
                STUDENT_ID,
                class_id,
                date(2038, 9, 1),
            )
            low_score = score_repository.create(
                connection,
                enrollment.enrollment_id,
                low_assessment.assessment_id,
                Decimal("4.99"),
            )
            exact_score = score_repository.create(
                connection,
                enrollment.enrollment_id,
                exact_assessment.assessment_id,
                Decimal("5.00"),
            )

        rule = academic.create_support_rule(
            subject_a_id,
            year_id,
            Decimal("5.00"),
        )
        assert rule.threshold == Decimal("5.00")
        with pytest.raises(DuplicateError):
            academic.create_support_rule(subject_a_id, year_id, Decimal("4.00"))

        support = SupportService(db)
        intervention = support.detect_from_score(low_score.score_id)
        assert intervention is not None
        assert intervention.status == InterventionStatus.DETECTED
        assert support.detect_from_score(exact_score.score_id) is None

        with pytest.raises(BusinessRuleError):
            academic.update_assessment(
                low_assessment.assessment_id,
                subject_b_id,
                year_id,
                ASSESSMENT_LOW,
                1,
                "QUIZ",
                date(2038, 10, 1),
                AssessmentStatus.ACTIVE,
            )

        academic.set_assessment_active(low_assessment.assessment_id, False)
        active_ids = {
            item.assessment_id
            for item in academic.list_active_assessments(year_id, subject_a_id)
        }
        assert low_assessment.assessment_id not in active_ids
        assert exact_assessment.assessment_id in active_ids
        all_ids = {
            item.assessment_id
            for item in academic.list_assessments(year_id, subject_a_id)
        }
        assert low_assessment.assessment_id in all_ids

        updated_rule = academic.update_support_rule_threshold(
            rule.rule_id,
            Decimal("4.50"),
        )
        assert updated_rule.threshold == Decimal("4.50")
        with db.transaction() as connection:
            preserved = intervention_repository.get_by_id(
                connection,
                intervention.intervention_id,
            )
            stored_low_score = score_repository.get_by_id(
                connection,
                low_score.score_id,
            )
        assert preserved is not None
        assert preserved.trigger_score_id == low_score.score_id
        assert preserved.status == InterventionStatus.DETECTED
        assert stored_low_score is not None
        assert stored_low_score.score == Decimal("4.99")

        academic.set_support_rule_active(rule.rule_id, False)
        replacement = academic.create_support_rule(
            subject_a_id,
            year_id,
            Decimal("4.75"),
        )
        assert replacement.is_active is True
        assert len(academic.list_catalog_support_rules(year_id, subject_a_id)) == 2

        academic.set_subject_active(subject_a_id, False)
        assert subject_a_id not in {
            item[0] for item in academic.list_active_subjects()
        }
        assert low_assessment.assessment_id in {
            item.assessment_id
            for item in academic.list_assessments(year_id, subject_a_id)
        }
    finally:
        cleanup(db)
