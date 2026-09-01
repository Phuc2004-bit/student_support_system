from datetime import date
from decimal import Decimal

from config.database import db_settings
from database.connection import DatabaseManager
from models.dto import StudentCreateData
from models.enums import (
    InterventionStatus,
    ReviewResult,
)
from repositories import (
    AcademicRepository,
    EnrollmentRepository,
    InterventionRepository,
    ScoreRepository,
    StudentRepository,
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
            DELETE FROM dbo.INTERVENTION_REVIEWS
            WHERE intervention_id IN
            (
                SELECT intervention_id
                FROM dbo.INTERVENTIONS
                WHERE enrollment_id IN
                (
                    SELECT enrollment_id
                    FROM dbo.STUDENT_ENROLLMENTS
                    WHERE student_id = 'test-int-student'
                )
            )
            """
        )

        cursor.execute(
            """
            DELETE FROM dbo.INTERVENTIONS
            WHERE enrollment_id IN
            (
                SELECT enrollment_id
                FROM dbo.STUDENT_ENROLLMENTS
                WHERE student_id = 'test-int-student'
            )
            """
        )

        cursor.execute(
            """
            DELETE FROM dbo.SCORES
            WHERE enrollment_id IN
            (
                SELECT enrollment_id
                FROM dbo.STUDENT_ENROLLMENTS
                WHERE student_id = 'test-int-student'
            )
            """
        )

        cursor.execute(
            """
            DELETE FROM dbo.ASSESSMENTS
            WHERE assessment_name IN
            (
                N'TEST_TRIGGER_ASSESSMENT',
                N'TEST_REVIEW_ASSESSMENT'
            )
            """
        )

        cursor.execute(
            """
            DELETE FROM dbo.STUDENT_ENROLLMENTS
            WHERE student_id = 'test-int-student'
            """
        )

        cursor.execute(
            """
            DELETE FROM dbo.STUDENTS
            WHERE student_id = 'test-int-student'
            """
        )

        cursor.execute(
            """
            DELETE FROM dbo.CLASSES
            WHERE class_name = N'TEST_INT_10A1'
            """
        )

        cursor.execute(
            """
            DELETE FROM dbo.SUBJECTS
            WHERE subject_code = 'TEST_INT_TOAN'
            """
        )

        cursor.execute(
            """
            DELETE FROM dbo.SCHOOL_YEARS
            WHERE year_name = 'TEST_INT_2026_2027'
            """
        )


def test_intervention_repository_flow():
    test_db = get_test_db()

    academic_repo = AcademicRepository()
    student_repo = StudentRepository()
    enrollment_repo = EnrollmentRepository()
    score_repo = ScoreRepository()
    intervention_repo = InterventionRepository()

    cleanup(test_db)

    with test_db.transaction() as connection:
        cursor = connection.cursor()

        # grade_number là UNIQUE; GRADES là dữ liệu nền dùng chung.
        # Tái sử dụng Khối 10 nếu đã tồn tại.
        cursor.execute(
            """
            SELECT grade_id
            FROM dbo.GRADES
            WHERE grade_number = ?
            """,
            10,
        )
        grade_row = cursor.fetchone()

        if grade_row is not None:
            grade_id = grade_row[0]
        else:
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
                "Khối 10",
            )
            grade_id = cursor.fetchone()[0]

        school_year_id = academic_repo.create_school_year(
            connection,
            "TEST_INT_2026_2027",
            date(2026, 9, 7),
            date(2027, 5, 31),
            False,
        )

        class_id = academic_repo.create_class(
            connection,
            "TEST_INT_10A1",
            grade_id,
            school_year_id,
        )

        subject_id = academic_repo.create_subject(
            connection,
            "TEST_INT_TOAN",
            "Toán Intervention Test",
        )

        trigger_assessment = academic_repo.create_assessment(
            connection,
            subject_id,
            school_year_id,
            "TEST_TRIGGER_ASSESSMENT",
            1,
            "MIDTERM",
            date(2026, 10, 15),
        )

        review_assessment = academic_repo.create_assessment(
            connection,
            subject_id,
            school_year_id,
            "TEST_REVIEW_ASSESSMENT",
            1,
            "REVIEW",
            date(2026, 11, 15),
        )

        student_repo.create(
            connection,
            "test-int-student",
            StudentCreateData(
                student_code="TEST_INT_HS001",
                full_name="Học sinh Intervention Test",
            ),
        )

        enrollment = enrollment_repo.create(
            connection,
            "test-int-student",
            class_id,
            date(2026, 9, 7),
        )

        trigger_score = score_repo.create(
            connection,
            enrollment.enrollment_id,
            trigger_assessment.assessment_id,
            Decimal("2.80"),
        )

        intervention = intervention_repo.create(
            connection,
            enrollment.enrollment_id,
            subject_id,
            trigger_score.score_id,
            date(2026, 10, 15),
        )

        assert intervention.status == InterventionStatus.DETECTED
        assert intervention.responsible_user_id is None

        intervention_id = intervention.intervention_id

        review_score = score_repo.create(
            connection,
            enrollment.enrollment_id,
            review_assessment.assessment_id,
            Decimal("3.20"),
        )

        review_score_id = review_score.score_id

    with test_db.transaction() as connection:
        open_case = intervention_repo.get_open(
            connection,
            enrollment.enrollment_id,
            subject_id,
        )

        assert open_case is not None
        assert open_case.intervention_id == intervention_id

    with test_db.transaction() as connection:
        in_progress = intervention_repo.update_status(
            connection,
            intervention_id,
            InterventionStatus.IN_PROGRESS,
        )

        assert in_progress is not None
        assert in_progress.status == InterventionStatus.IN_PROGRESS

    with test_db.transaction() as connection:
        review = intervention_repo.create_review(
            connection,
            intervention_id,
            review_score_id,
            date(2026, 11, 15),
            ReviewResult.NOT_PASSED,
            "Tiếp tục bổ trợ.",
        )

        assert review.result == ReviewResult.NOT_PASSED

    with test_db.transaction() as connection:
        reviews = intervention_repo.list_reviews(
            connection,
            intervention_id,
        )

        assert len(reviews) == 1
        assert reviews[0].score_id == review_score_id

    with test_db.transaction() as connection:
        completed = intervention_repo.update_status(
            connection,
            intervention_id,
            InterventionStatus.COMPLETED,
        )

        assert completed is not None
        assert completed.status == InterventionStatus.COMPLETED

    with test_db.transaction() as connection:
        open_case = intervention_repo.get_open(
            connection,
            enrollment.enrollment_id,
            subject_id,
        )

        assert open_case is None

    cleanup(test_db)