from datetime import date
from decimal import Decimal

from config.database import db_settings
from database.connection import DatabaseManager
from models.dto import StudentCreateData
from models.enums import (
    InterventionStatus,
    ReviewResult,
    UserRole,
)
from repositories import (
    AcademicRepository,
    InterventionRepository,
    SupportRuleRepository,
    UserRepository,
)
from services import (
    EnrollmentService,
    ScoreService,
    StudentService,
    SupportService,
)


TEST_CODE = "TRV_HS001"
TEST_YEAR = "TRV_2026_2027"


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
                WHERE subject_code = 'TRV_TOAN'
            )
            """
        )

        cursor.execute(
            """
            DELETE FROM dbo.ASSESSMENTS
            WHERE assessment_name IN
            (
                N'TRV_TRIGGER',
                N'TRV_REVIEW_1',
                N'TRV_REVIEW_2'
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
            WHERE class_name = N'TRV_10A1'
            """
        )

        cursor.execute(
            """
            DELETE FROM dbo.SUBJECTS
            WHERE subject_code = 'TRV_TOAN'
            """
        )

        cursor.execute(
            """
            DELETE FROM dbo.SCHOOL_YEARS
            WHERE year_name = ?
            """,
            TEST_YEAR,
        )

        cursor.execute(
            """
            DELETE FROM dbo.USERS
            WHERE username = 'trv_teacher'
            """
        )


def test_support_review_golden_flow():
    test_db = get_test_db()

    academic_repo = AcademicRepository()
    rule_repo = SupportRuleRepository()
    user_repo = UserRepository()
    intervention_repo = InterventionRepository()

    student_service = StudentService(test_db)
    enrollment_service = EnrollmentService(test_db)
    score_service = ScoreService(test_db)
    support_service = SupportService(test_db)

    cleanup(test_db)

    try:
        # =============================================
        # SEED
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
                "TRV_10A1",
                grade_id,
                school_year_id,
            )

            subject_id = academic_repo.create_subject(
                connection,
                "TRV_TOAN",
                "Toán Review Test",
            )

            trigger_assessment = (
                academic_repo.create_assessment(
                    connection,
                    subject_id,
                    school_year_id,
                    "TRV_TRIGGER",
                    1,
                    "MIDTERM",
                    date(2026, 10, 15),
                )
            )

            review_1_assessment = (
                academic_repo.create_assessment(
                    connection,
                    subject_id,
                    school_year_id,
                    "TRV_REVIEW_1",
                    1,
                    "REVIEW",
                    date(2026, 11, 15),
                )
            )

            review_2_assessment = (
                academic_repo.create_assessment(
                    connection,
                    subject_id,
                    school_year_id,
                    "TRV_REVIEW_2",
                    1,
                    "REVIEW",
                    date(2026, 12, 15),
                )
            )

            rule_repo.create(
                connection,
                subject_id,
                school_year_id,
                Decimal("3.50"),
            )

            teacher = user_repo.create(
                connection,
                "trv_teacher",
                "$2b$12$fakehash",
                "Giáo viên Review Test",
                UserRole.TEACHER,
            )

        # =============================================
        # STUDENT + ENROLLMENT
        # =============================================
        student = student_service.create_student(
            StudentCreateData(
                student_code=TEST_CODE,
                full_name="Học sinh Review Test",
            )
        )

        enrollment = enrollment_service.enroll_student(
            student.student_id,
            class_id,
            date(2026, 9, 7),
        )

        # =============================================
        # 2.80 → DETECTED
        # =============================================
        trigger_score = score_service.create_score(
            enrollment.enrollment_id,
            trigger_assessment.assessment_id,
            Decimal("2.80"),
        )

        intervention = support_service.detect_from_score(
            trigger_score.score_id
        )

        assert intervention is not None

        intervention_id = intervention.intervention_id

        # =============================================
        # DETECTED → PLANNED
        # =============================================
        support_service.plan_intervention(
            intervention_id,
            teacher.user_id,
            date(2026, 10, 20),
            "Phụ đạo nhóm nhỏ",
        )

        # =============================================
        # PLANNED → IN_PROGRESS
        # =============================================
        support_service.start_intervention(
            intervention_id
        )

        # =============================================
        # IN_PROGRESS → WAITING_REVIEW
        # =============================================
        support_service.mark_waiting_review(
            intervention_id
        )

        # =============================================
        # REVIEW 1: 3.20 < 3.50
        # → NOT_PASSED
        # → CONTINUE
        # =============================================
        review_score_1 = score_service.create_score(
            enrollment.enrollment_id,
            review_1_assessment.assessment_id,
            Decimal("3.20"),
        )

        after_review_1 = (
            support_service.review_intervention(
                intervention_id,
                review_score_1.score_id,
                date(2026, 11, 15),
                "Chưa đạt ngưỡng.",
            )
        )

        assert (
            after_review_1.status
            == InterventionStatus.CONTINUE
        )

        # =============================================
        # CONTINUE → IN_PROGRESS
        # =============================================
        support_service.continue_intervention(
            intervention_id
        )

        # =============================================
        # IN_PROGRESS → WAITING_REVIEW
        # =============================================
        support_service.mark_waiting_review(
            intervention_id
        )

        # =============================================
        # REVIEW 2: 4.10 >= 3.50
        # → PASSED
        # → COMPLETED
        # =============================================
        review_score_2 = score_service.create_score(
            enrollment.enrollment_id,
            review_2_assessment.assessment_id,
            Decimal("4.10"),
        )

        after_review_2 = (
            support_service.review_intervention(
                intervention_id,
                review_score_2.score_id,
                date(2026, 12, 15),
                "Đã đạt ngưỡng.",
            )
        )

        assert (
            after_review_2.status
            == InterventionStatus.COMPLETED
        )

        # =============================================
        # REVIEW HISTORY
        # =============================================
        with test_db.transaction() as connection:
            reviews = intervention_repo.list_reviews(
                connection,
                intervention_id,
            )

        assert len(reviews) == 2

        assert (
            reviews[0].result
            == ReviewResult.NOT_PASSED
        )

        assert (
            reviews[1].result
            == ReviewResult.PASSED
        )

        assert (
            reviews[0].score_id
            == review_score_1.score_id
        )

        assert (
            reviews[1].score_id
            == review_score_2.score_id
        )

        # =============================================
        # COMPLETED → NO OPEN CASE
        # =============================================
        open_case = (
            support_service.get_open_intervention(
                enrollment.enrollment_id,
                subject_id,
            )
        )

        assert open_case is None

    finally:
        cleanup(test_db)