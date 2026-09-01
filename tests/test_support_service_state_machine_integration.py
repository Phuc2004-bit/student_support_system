from datetime import date
from decimal import Decimal

from config.database import db_settings
from database.connection import DatabaseManager
from exceptions import InvalidStateTransitionError
from models.dto import StudentCreateData
from models.enums import InterventionStatus, UserRole
from repositories import (
    AcademicRepository,
    SupportRuleRepository,
    UserRepository,
)
from services import (
    EnrollmentService,
    ScoreService,
    StudentService,
    SupportService,
)


TEST_CODE = "TSM_HS001"
TEST_YEAR = "TSM_2026_2027"


def get_test_db() -> DatabaseManager:
    connection_string = db_settings.connection_string().replace(
        "DATABASE=student_support_db;",
        "DATABASE=student_support_db_test;",
    )

    return DatabaseManager(connection_string)


def cleanup(test_db: DatabaseManager) -> None:
    with test_db.transaction() as connection:
        cursor = connection.cursor()

        # Xóa review trước vì có khóa ngoại tới intervention
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

        # Xóa intervention
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

        # Xóa score
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

        # Xóa support rule
        cursor.execute(
            """
            DELETE FROM dbo.SUPPORT_RULES
            WHERE subject_id IN
            (
                SELECT subject_id
                FROM dbo.SUBJECTS
                WHERE subject_code = 'TSM_TOAN'
            )
            """
        )

        # Xóa assessment
        cursor.execute(
            """
            DELETE FROM dbo.ASSESSMENTS
            WHERE assessment_name = N'TSM_ASSESSMENT'
            """
        )

        # Xóa enrollment
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

        # Xóa student
        cursor.execute(
            """
            DELETE FROM dbo.STUDENTS
            WHERE student_code = ?
            """,
            TEST_CODE,
        )

        # Xóa class
        cursor.execute(
            """
            DELETE FROM dbo.CLASSES
            WHERE class_name = N'TSM_10A1'
            """
        )

        # Xóa subject
        cursor.execute(
            """
            DELETE FROM dbo.SUBJECTS
            WHERE subject_code = 'TSM_TOAN'
            """
        )

        # Xóa school year
        cursor.execute(
            """
            DELETE FROM dbo.SCHOOL_YEARS
            WHERE year_name = ?
            """,
            TEST_YEAR,
        )

        # Xóa user test
        cursor.execute(
            """
            DELETE FROM dbo.USERS
            WHERE username = 'tsm_teacher'
            """
        )


def test_support_state_machine():
    test_db = get_test_db()

    academic_repo = AcademicRepository()
    rule_repo = SupportRuleRepository()
    user_repo = UserRepository()

    student_service = StudentService(test_db)
    enrollment_service = EnrollmentService(test_db)
    score_service = ScoreService(test_db)
    support_service = SupportService(test_db)

    # Dọn dữ liệu test cũ trước khi chạy
    cleanup(test_db)

    try:
        # =================================================
        # 1. TẠO DỮ LIỆU NỀN
        # =================================================
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
                "TSM_10A1",
                grade_id,
                school_year_id,
            )

            subject_id = academic_repo.create_subject(
                connection,
                "TSM_TOAN",
                "Toán State Machine",
            )

            assessment = academic_repo.create_assessment(
                connection,
                subject_id,
                school_year_id,
                "TSM_ASSESSMENT",
                1,
                "MIDTERM",
                date(2026, 10, 15),
            )

            rule_repo.create(
                connection,
                subject_id,
                school_year_id,
                Decimal("3.50"),
            )

            teacher = user_repo.create(
                connection,
                "tsm_teacher",
                "$2b$12$fakehash",
                "Giáo viên Test",
                UserRole.TEACHER,
            )

        # =================================================
        # 2. TẠO HỌC SINH
        # =================================================
        student = student_service.create_student(
            StudentCreateData(
                student_code=TEST_CODE,
                full_name="Học sinh State Machine",
            )
        )

        # =================================================
        # 3. XẾP HỌC SINH VÀO LỚP
        # =================================================
        enrollment = enrollment_service.enroll_student(
            student.student_id,
            class_id,
            date(2026, 9, 7),
        )

        # =================================================
        # 4. NHẬP ĐIỂM 2.80
        # =================================================
        score = score_service.create_score(
            enrollment.enrollment_id,
            assessment.assessment_id,
            Decimal("2.80"),
        )

        # =================================================
        # 5. 2.80 < 3.50 => DETECTED
        # =================================================
        intervention = support_service.detect_from_score(
            score.score_id
        )

        assert intervention is not None

        assert (
            intervention.status
            == InterventionStatus.DETECTED
        )

        intervention_id = intervention.intervention_id

        # =================================================
        # 6. THỬ SAI:
        # DETECTED -> IN_PROGRESS
        # PHẢI BỊ CHẶN
        # =================================================
        invalid_blocked = False

        try:
            support_service.start_intervention(
                intervention_id
            )

        except InvalidStateTransitionError:
            invalid_blocked = True

        assert invalid_blocked is True

        # =================================================
        # 7. ĐÚNG:
        # DETECTED -> PLANNED
        # =================================================
        planned = support_service.plan_intervention(
            intervention_id,
            teacher.user_id,
            date(2026, 10, 20),
            "Phụ đạo theo nhóm nhỏ",
            "Theo dõi tiến độ hàng tuần",
        )

        assert (
            planned.status
            == InterventionStatus.PLANNED
        )

        assert (
            planned.responsible_user_id
            == teacher.user_id
        )

        # =================================================
        # 8. PLANNED -> IN_PROGRESS
        # =================================================
        started = support_service.start_intervention(
            intervention_id
        )

        assert (
            started.status
            == InterventionStatus.IN_PROGRESS
        )

        # =================================================
        # 9. IN_PROGRESS -> WAITING_REVIEW
        # =================================================
        waiting = support_service.mark_waiting_review(
            intervention_id
        )

        assert (
            waiting.status
            == InterventionStatus.WAITING_REVIEW
        )

        # =================================================
        # 10. THỬ SAI:
        # WAITING_REVIEW -> IN_PROGRESS
        # KHÔNG ĐƯỢC PHÉP
        # =================================================
        invalid_blocked = False

        try:
            support_service.start_intervention(
                intervention_id
            )

        except InvalidStateTransitionError:
            invalid_blocked = True

        assert invalid_blocked is True

    finally:
        # Luôn dọn dữ liệu dù test pass hay fail
        cleanup(test_db)