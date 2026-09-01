from datetime import date
from decimal import Decimal

from config.database import db_settings
from database.connection import DatabaseManager
from models.dto import StudentCreateData
from models.enums import InterventionStatus
from repositories import (
    AcademicRepository,
    SupportRuleRepository,
)
from services import (
    EnrollmentService,
    ScoreService,
    StudentService,
    SupportService,
)


TEST_CODE = "TEST_SUPPORT_SVC_01"
TEST_YEAR = "TSUP_2026_2027"


def get_test_db() -> DatabaseManager:
    connection_string = db_settings.connection_string().replace(
        "DATABASE=student_support_db;",
        "DATABASE=student_support_db_test;",
    )

    return DatabaseManager(connection_string)


def cleanup(test_db: DatabaseManager) -> None:
    with test_db.transaction() as connection:
        cursor = connection.cursor()

        # Reviews phải xóa trước interventions
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
                    WHERE student_id IN
                    (
                        SELECT student_id
                        FROM dbo.STUDENTS
                        WHERE student_code = ?
                    )
                )
            )
            """,
            TEST_CODE,
        )

        cursor.execute(
            """
            DELETE FROM dbo.INTERVENTIONS
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
            DELETE FROM dbo.SUPPORT_RULES
            WHERE subject_id IN
            (
                SELECT subject_id
                FROM dbo.SUBJECTS
                WHERE subject_code = 'TSUP_TOAN'
            )
            """
        )

        cursor.execute(
            """
            DELETE FROM dbo.ASSESSMENTS
            WHERE assessment_name IN
            (
                N'TSUP_LOW',
                N'TSUP_BOUNDARY'
            )
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
            WHERE class_name = N'TSUP_10A1'
            """
        )

        cursor.execute(
            """
            DELETE FROM dbo.SUBJECTS
            WHERE subject_code = 'TSUP_TOAN'
            """
        )

        cursor.execute(
            """
            DELETE FROM dbo.SCHOOL_YEARS
            WHERE year_name = ?
            """,
            TEST_YEAR,
        )


def test_support_detection_flow():
    test_db = get_test_db()

    academic_repo = AcademicRepository()
    rule_repo = SupportRuleRepository()

    student_service = StudentService(test_db)
    enrollment_service = EnrollmentService(test_db)
    score_service = ScoreService(test_db)
    support_service = SupportService(test_db)

    cleanup(test_db)

    try:
        # =============================================
        # ACADEMIC DATA + RULE
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
                    TEST_YEAR,
                    date(2026, 9, 7),
                    date(2027, 5, 31),
                    False,
                )
            )

            class_id = academic_repo.create_class(
                connection,
                "TSUP_10A1",
                grade_id,
                school_year_id,
            )

            subject_id = academic_repo.create_subject(
                connection,
                "TSUP_TOAN",
                "Toán Support Test",
            )

            low_assessment = (
                academic_repo.create_assessment(
                    connection,
                    subject_id,
                    school_year_id,
                    "TSUP_LOW",
                    1,
                    "MIDTERM",
                    date(2026, 10, 15),
                )
            )

            boundary_assessment = (
                academic_repo.create_assessment(
                    connection,
                    subject_id,
                    school_year_id,
                    "TSUP_BOUNDARY",
                    1,
                    "REVIEW",
                    date(2026, 11, 15),
                )
            )

            rule_repo.create(
                connection,
                subject_id,
                school_year_id,
                Decimal("3.50"),
            )

        # =============================================
        # STUDENT + ENROLLMENT
        # =============================================
        student = student_service.create_student(
            StudentCreateData(
                student_code=TEST_CODE,
                full_name="Học sinh Support Service",
            )
        )

        enrollment = enrollment_service.enroll_student(
            student.student_id,
            class_id,
            date(2026, 9, 7),
        )

        # =============================================
        # 2.80 < 3.50 → DETECTED
        # =============================================
        low_score = score_service.create_score(
            enrollment.enrollment_id,
            low_assessment.assessment_id,
            Decimal("2.80"),
        )

        intervention = support_service.detect_from_score(
            low_score.score_id
        )

        assert intervention is not None
        assert (
            intervention.status
            == InterventionStatus.DETECTED
        )

        first_intervention_id = (
            intervention.intervention_id
        )

        # =============================================
        # DETECT SAME SCORE AGAIN
        # → MUST NOT CREATE DUPLICATE CASE
        # =============================================
        same_case = support_service.detect_from_score(
            low_score.score_id
        )

        assert same_case is not None
        assert (
            same_case.intervention_id
            == first_intervention_id
        )

        # =============================================
        # 3.50 == THRESHOLD
        # → NOT BELOW THRESHOLD
        # =============================================
        boundary_score = score_service.create_score(
            enrollment.enrollment_id,
            boundary_assessment.assessment_id,
            Decimal("3.50"),
        )

        result = support_service.detect_from_score(
            boundary_score.score_id
        )

        assert result is None

    finally:
        cleanup(test_db)