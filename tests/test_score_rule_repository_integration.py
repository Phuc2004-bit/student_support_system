from datetime import date
from decimal import Decimal

from config.database import db_settings
from database.connection import DatabaseManager
from models.dto import StudentCreateData
from repositories import (
    AcademicRepository,
    EnrollmentRepository,
    ScoreRepository,
    StudentRepository,
    SupportRuleRepository,
)


def get_test_db() -> DatabaseManager:
    connection_string = db_settings.connection_string().replace(
        "DATABASE=student_support_db;",
        "DATABASE=student_support_db_test;",
    )

    return DatabaseManager(connection_string)


def cleanup(test_db: DatabaseManager) -> None:
    with test_db.transaction() as connection:
        cursor = connection.cursor()

        cursor.execute(
            """
            DELETE FROM dbo.SCORES
            WHERE enrollment_id IN
            (
                SELECT enrollment_id
                FROM dbo.STUDENT_ENROLLMENTS
                WHERE student_id = 'test-score-student'
            )
            """
        )

        cursor.execute(
            """
            DELETE FROM dbo.SUPPORT_RULES
            WHERE subject_id IN
            (
                SELECT subject_id
                FROM dbo.SUBJECTS
                WHERE subject_code = 'TEST_SCORE_TOAN'
            )
            """
        )

        cursor.execute(
            """
            DELETE FROM dbo.ASSESSMENTS
            WHERE assessment_name = N'TEST_SCORE_ASSESSMENT'
            """
        )

        cursor.execute(
            """
            DELETE FROM dbo.STUDENT_ENROLLMENTS
            WHERE student_id = 'test-score-student'
            """
        )

        cursor.execute(
            """
            DELETE FROM dbo.STUDENTS
            WHERE student_id = 'test-score-student'
            """
        )

        cursor.execute(
            """
            DELETE FROM dbo.CLASSES
            WHERE class_name = N'TEST_SCORE_10A1'
            """
        )

        cursor.execute(
            """
            DELETE FROM dbo.SUBJECTS
            WHERE subject_code = 'TEST_SCORE_TOAN'
            """
        )

        cursor.execute(
            """
            DELETE FROM dbo.SCHOOL_YEARS
            WHERE year_name = 'TEST_SCORE_2026_2027'
            """
        )

        cursor.execute(
            """
            DELETE FROM dbo.GRADES
            WHERE grade_number = 10
              AND grade_name = N'TEST_SCORE_GRADE_10'
            """
        )


def test_score_and_rule_repository_flow():
    test_db = get_test_db()

    academic_repo = AcademicRepository()
    student_repo = StudentRepository()
    enrollment_repo = EnrollmentRepository()
    score_repo = ScoreRepository()
    rule_repo = SupportRuleRepository()

    cleanup(test_db)

    with test_db.transaction() as connection:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO dbo.GRADES
            (
                grade_number,
                grade_name
            )
            OUTPUT INSERTED.grade_id
            VALUES (?, ?)
            """,
            10,
            "TEST_SCORE_GRADE_10",
        )

        grade_id = cursor.fetchone()[0]

        school_year_id = academic_repo.create_school_year(
            connection,
            "TEST_SCORE_2026_2027",
            date(2026, 9, 7),
            date(2027, 5, 31),
            False,
        )

        class_id = academic_repo.create_class(
            connection,
            "TEST_SCORE_10A1",
            grade_id,
            school_year_id,
        )

        subject_id = academic_repo.create_subject(
            connection,
            "TEST_SCORE_TOAN",
            "Toán Test Score",
        )

        assessment = academic_repo.create_assessment(
            connection,
            subject_id,
            school_year_id,
            "TEST_SCORE_ASSESSMENT",
            1,
            "MIDTERM",
            date(2026, 10, 15),
        )

        student_repo.create(
            connection,
            "test-score-student",
            StudentCreateData(
                student_code="TEST_SCORE_HS001",
                full_name="Học sinh Score Test",
            ),
        )

        enrollment = enrollment_repo.create(
            connection,
            "test-score-student",
            class_id,
            date(2026, 9, 7),
        )

        rule = rule_repo.create(
            connection,
            subject_id,
            school_year_id,
            Decimal("3.50"),
        )

        score = score_repo.create(
            connection,
            enrollment.enrollment_id,
            assessment.assessment_id,
            Decimal("3.49"),
        )

        assert rule.threshold == Decimal("3.50")
        assert score.score == Decimal("3.49")

        score_id = score.score_id

    with test_db.transaction() as connection:
        active_rule = rule_repo.get_active_rule(
            connection,
            subject_id,
            school_year_id,
        )

        assert active_rule is not None
        assert active_rule.threshold == Decimal("3.50")

        stored_score = score_repo.get_by_id(
            connection,
            score_id,
        )

        assert stored_score is not None
        assert stored_score.score == Decimal("3.49")

        assert stored_score.score < active_rule.threshold

    with test_db.transaction() as connection:
        updated = score_repo.update(
            connection,
            score_id,
            Decimal("3.50"),
        )

        assert updated is not None
        assert updated.score == Decimal("3.50")

    with test_db.transaction() as connection:
        active_rule = rule_repo.get_active_rule(
            connection,
            subject_id,
            school_year_id,
        )

        stored_score = score_repo.get_by_id(
            connection,
            score_id,
        )

        assert active_rule is not None
        assert stored_score is not None

        assert not (
            stored_score.score
            < active_rule.threshold
        )

    cleanup(test_db)