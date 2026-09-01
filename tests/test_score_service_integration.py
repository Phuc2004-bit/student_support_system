from datetime import date
from decimal import Decimal

from config.database import db_settings
from database.connection import DatabaseManager
from exceptions import DuplicateError, ValidationError
from models.dto import StudentCreateData
from repositories import AcademicRepository
from services import (
    EnrollmentService,
    ScoreService,
    StudentService,
)


TEST_CODE = "TEST_SCORE_SVC_001"


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
                WHERE student_id IN
                (
                    SELECT student_id
                    FROM dbo.STUDENTS
                    WHERE student_code = ?
                )
            )
            """,
            TEST_CODE,
        )

        cursor.execute(
            """
            DELETE FROM dbo.ASSESSMENTS
            WHERE assessment_name = N'TEST_SCORE_SVC_ASSESSMENT'
            """
        )

        cursor.execute(
            """
            DELETE FROM dbo.STUDENT_ENROLLMENTS
            WHERE student_id IN
            (
                SELECT student_id
                FROM dbo.STUDENTS
                WHERE student_code = ?
            )
            """,
            TEST_CODE,
        )

        cursor.execute(
            """
            DELETE FROM dbo.STUDENTS
            WHERE student_code = ?
            """,
            TEST_CODE,
        )

        cursor.execute(
            """
            DELETE FROM dbo.CLASSES
            WHERE class_name = N'TEST_SCORE_SVC_10A1'
            """
        )

        cursor.execute(
            """
            DELETE FROM dbo.SUBJECTS
            WHERE subject_code = 'TEST_SCORE_SVC_TOAN'
            """
        )

        cursor.execute(
            """
            DELETE FROM dbo.SCHOOL_YEARS
            WHERE year_name = 'TSVC_2026_2027'
            """
        )


def test_score_service_flow():
    test_db = get_test_db()

    student_service = StudentService(test_db)
    enrollment_service = EnrollmentService(test_db)
    score_service = ScoreService(test_db)
    academic_repo = AcademicRepository()

    cleanup(test_db)

    try:
        # =============================================
        # SEED ACADEMIC DATA
        # =============================================
        with test_db.transaction() as connection:
            cursor = connection.cursor()

            # grade_number là UNIQUE; nhiều integration test cùng dùng khối 10.
            # Tái sử dụng grade nếu đã tồn tại để test suite chạy độc lập, lặp lại được.
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

            school_year_id = (
                academic_repo.create_school_year(
                    connection,
                    "TSVC_2026_2027",
                    date(2026, 9, 7),
                    date(2027, 5, 31),
                    False,
                )
            )

            class_id = academic_repo.create_class(
                connection,
                "TEST_SCORE_SVC_10A1",
                grade_id,
                school_year_id,
            )

            subject_id = academic_repo.create_subject(
                connection,
                "TEST_SCORE_SVC_TOAN",
                "Toán Score Service",
            )

            assessment = academic_repo.create_assessment(
                connection,
                subject_id,
                school_year_id,
                "TEST_SCORE_SVC_ASSESSMENT",
                1,
                "MIDTERM",
                date(2026, 10, 15),
            )

        # =============================================
        # STUDENT + ENROLLMENT
        # =============================================
        student = student_service.create_student(
            StudentCreateData(
                student_code=TEST_CODE,
                full_name="Học sinh Score Service",
            )
        )

        enrollment = enrollment_service.enroll_student(
            student.student_id,
            class_id,
            date(2026, 9, 7),
        )

        # =============================================
        # CREATE SCORE
        # =============================================
        score = score_service.create_score(
            enrollment.enrollment_id,
            assessment.assessment_id,
            Decimal("2.80"),
        )

        assert score.score == Decimal("2.80")

        score_id = score.score_id

        # =============================================
        # READ
        # =============================================
        found = score_service.get_score(score_id)

        assert found.score_id == score_id
        assert found.score == Decimal("2.80")

        # =============================================
        # DUPLICATE SCORE MUST BE BLOCKED
        # =============================================
        duplicate_blocked = False

        try:
            score_service.create_score(
                enrollment.enrollment_id,
                assessment.assessment_id,
                Decimal("3.00"),
            )
        except DuplicateError:
            duplicate_blocked = True

        assert duplicate_blocked is True

        # =============================================
        # UPDATE
        # =============================================
        updated = score_service.update_score(
            score_id,
            Decimal("3.40"),
        )

        assert updated.score == Decimal("3.40")

        # =============================================
        # LIST
        # =============================================
        scores = (
            score_service.list_scores_by_enrollment(
                enrollment.enrollment_id
            )
        )

        assert len(scores) == 1
        assert scores[0].score_id == score_id

        # =============================================
        # SCORE > 10 MUST BE BLOCKED
        # =============================================
        invalid_blocked = False

        try:
            score_service.update_score(
                score_id,
                Decimal("10.01"),
            )
        except ValidationError:
            invalid_blocked = True

        assert invalid_blocked is True

    finally:
        cleanup(test_db)