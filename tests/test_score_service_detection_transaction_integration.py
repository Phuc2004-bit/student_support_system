from datetime import date
from decimal import Decimal

import pytest

from config.database import db_settings
from database.connection import DatabaseManager
from exceptions import MissingSupportRuleError
from models.dto import StudentCreateData
from models.enums import InterventionStatus
from repositories import (
    AcademicRepository,
    InterventionRepository,
    SupportRuleRepository,
)
from services import (
    EnrollmentService,
    ScoreService,
    StudentService,
)


TEST_CODE = "TSD_HS001"
TEST_YEAR = "TSD_2026_2027"
TEST_CLASS = "TSD_10A1"
TEST_SUBJECT_CODE = "TSD_TOAN"


def get_test_db() -> DatabaseManager:
    connection_string = db_settings.connection_string().replace(
        "DATABASE=student_support_db;",
        "DATABASE=student_support_db_test;",
    )
    return DatabaseManager(connection_string)


def cleanup(db: DatabaseManager) -> None:
    """
    Xóa toàn bộ dữ liệu test theo đúng thứ tự khóa ngoại.
    Không đụng vào dữ liệu thật ngoài các mã TSD_*.
    """
    with db.transaction() as connection:
        cursor = connection.cursor()

        # 1. Review
        cursor.execute(
            """
            DELETE FROM INTERVENTION_REVIEWS
            WHERE intervention_id IN (
                SELECT i.intervention_id
                FROM INTERVENTIONS i
                INNER JOIN STUDENT_ENROLLMENTS se
                    ON i.enrollment_id = se.enrollment_id
                INNER JOIN STUDENTS s
                    ON se.student_id = s.student_id
                WHERE s.student_code = ?
            )
            """,
            TEST_CODE,
        )

        # 2. Intervention
        cursor.execute(
            """
            DELETE FROM INTERVENTIONS
            WHERE enrollment_id IN (
                SELECT se.enrollment_id
                FROM STUDENT_ENROLLMENTS se
                INNER JOIN STUDENTS s
                    ON se.student_id = s.student_id
                WHERE s.student_code = ?
            )
            """,
            TEST_CODE,
        )

        # 3. Scores
        cursor.execute(
            """
            DELETE FROM SCORES
            WHERE enrollment_id IN (
                SELECT se.enrollment_id
                FROM STUDENT_ENROLLMENTS se
                INNER JOIN STUDENTS s
                    ON se.student_id = s.student_id
                WHERE s.student_code = ?
            )
            """,
            TEST_CODE,
        )

        # 4. Support rules
        cursor.execute(
            """
            DELETE FROM SUPPORT_RULES
            WHERE subject_id IN (
                SELECT subject_id
                FROM SUBJECTS
                WHERE subject_code = ?
            )
            """,
            TEST_SUBJECT_CODE,
        )

        # 5. Assessments
        cursor.execute(
            """
            DELETE FROM ASSESSMENTS
            WHERE assessment_name IN (
                'TSD_LOW',
                'TSD_HIGH',
                'TSD_ROLLBACK'
            )
            """
        )

        # 6. Enrollments
        cursor.execute(
            """
            DELETE FROM STUDENT_ENROLLMENTS
            WHERE student_id IN (
                SELECT student_id
                FROM STUDENTS
                WHERE student_code = ?
            )
            """,
            TEST_CODE,
        )

        # 7. Student
        cursor.execute(
            """
            DELETE FROM STUDENTS
            WHERE student_code = ?
            """,
            TEST_CODE,
        )

        # 8. Class
        cursor.execute(
            """
            DELETE FROM CLASSES
            WHERE class_name = ?
              AND school_year_id IN (
                  SELECT school_year_id
                  FROM SCHOOL_YEARS
                  WHERE year_name = ?
              )
            """,
            TEST_CLASS,
            TEST_YEAR,
        )

        # 9. Subject
        cursor.execute(
            """
            DELETE FROM SUBJECTS
            WHERE subject_code = ?
            """,
            TEST_SUBJECT_CODE,
        )

        # 10. School year
        cursor.execute(
            """
            DELETE FROM SCHOOL_YEARS
            WHERE year_name = ?
            """,
            TEST_YEAR,
        )

        # Không xóa grade 10 dùng chung của hệ thống.
        # Nếu test phải tạo grade 10 riêng, seed_base_data() sẽ tái sử dụng
        # grade_number = 10 nếu đã tồn tại.


def seed_base_data(db: DatabaseManager):
    academic_repo = AcademicRepository()
    rule_repo = SupportRuleRepository()

    with db.transaction() as connection:
        cursor = connection.cursor()

        # -------------------------------------------------
        # GRADE 10
        # Tái sử dụng nếu đã tồn tại để tránh vi phạm UNIQUE
        # -------------------------------------------------
        cursor.execute(
            """
            SELECT grade_id
            FROM GRADES
            WHERE grade_number = ?
            """,
            10,
        )
        row = cursor.fetchone()

        if row is not None:
            grade_id = row[0]
        else:
            cursor.execute(
                """
                INSERT INTO GRADES (
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

        # -------------------------------------------------
        # SCHOOL YEAR
        # -------------------------------------------------
        cursor.execute(
            """
            INSERT INTO SCHOOL_YEARS (
                year_name,
                start_date,
                end_date,
                is_current
            )
            OUTPUT INSERTED.school_year_id
            VALUES (?, ?, ?, ?)
            """,
            TEST_YEAR,
            date(2026, 9, 7),
            date(2027, 5, 31),
            0,
        )
        school_year_id = cursor.fetchone()[0]

        # -------------------------------------------------
        # CLASS
        # -------------------------------------------------
        cursor.execute(
            """
            INSERT INTO CLASSES (
                class_name,
                grade_id,
                school_year_id,
                homeroom_teacher,
                status
            )
            OUTPUT INSERTED.class_id
            VALUES (?, ?, ?, ?, ?)
            """,
            TEST_CLASS,
            grade_id,
            school_year_id,
            "Test Teacher",
            "ACTIVE",
        )
        class_id = cursor.fetchone()[0]

        # -------------------------------------------------
        # SUBJECT
        # -------------------------------------------------
        cursor.execute(
            """
            INSERT INTO SUBJECTS (
                subject_code,
                subject_name,
                is_active
            )
            OUTPUT INSERTED.subject_id
            VALUES (?, ?, ?)
            """,
            TEST_SUBJECT_CODE,
            "Toán Test",
            1,
        )
        subject_id = cursor.fetchone()[0]

        # -------------------------------------------------
        # ASSESSMENTS
        # -------------------------------------------------
        assessment_low = academic_repo.create_assessment(
            connection,
            subject_id,
            school_year_id,
            "TSD_LOW",
            1,
            "TEST",
            date(2026, 10, 10),
        )

        assessment_high = academic_repo.create_assessment(
            connection,
            subject_id,
            school_year_id,
            "TSD_HIGH",
            1,
            "TEST",
            date(2026, 10, 20),
        )

        assessment_rollback = academic_repo.create_assessment(
            connection,
            subject_id,
            school_year_id,
            "TSD_ROLLBACK",
            1,
            "TEST",
            date(2026, 10, 30),
        )

        # -------------------------------------------------
        # SUPPORT RULE: threshold = 3.50
        # -------------------------------------------------
        rule_repo.create(
            connection,
            subject_id,
            school_year_id,
            Decimal("3.50"),
            True,
        )

    # -----------------------------------------------------
    # STUDENT
    # StudentCreateData thực tế KHÔNG có field status
    # -----------------------------------------------------
    student_service = StudentService(db)

    student = student_service.create_student(
        StudentCreateData(
            student_code=TEST_CODE,
            full_name="Học Sinh Test Transaction",
            date_of_birth=date(2010, 1, 1),
            gender="Nam",
            phone=None,
            email=None,
            address=None,
        )
    )

    # -----------------------------------------------------
    # ENROLLMENT
    # API thực tế là enroll_student(), không phải
    # create_enrollment().
    # -----------------------------------------------------
    enrollment_service = EnrollmentService(db)

    enrollment = enrollment_service.enroll_student(
        student.student_id,
        class_id,
        date(2026, 9, 7),
    )

    return (
        enrollment,
        subject_id,
        school_year_id,
        assessment_low,
        assessment_high,
        assessment_rollback,
    )


def test_score_and_detection_same_transaction():
    db = get_test_db()

    cleanup(db)

    try:
        (
            enrollment,
            subject_id,
            school_year_id,
            assessment_low,
            assessment_high,
            assessment_rollback,
        ) = seed_base_data(db)

        score_service = ScoreService(db)

        # =================================================
        # CASE 1:
        # 2.80 < 3.50
        # => lưu score + tạo intervention DETECTED
        # =================================================
        low_score, intervention = (
            score_service.create_score_and_detect(
                enrollment.enrollment_id,
                assessment_low.assessment_id,
                Decimal("2.80"),
            )
        )

        assert low_score.score == Decimal("2.80")
        assert intervention is not None
        assert intervention.status == InterventionStatus.DETECTED
        assert intervention.trigger_score_id == low_score.score_id

        # =================================================
        # CASE 2:
        # 4.00 >= 3.50
        # => lưu score
        # => KHÔNG tạo intervention mới
        # => KHÔNG tự hoàn thành intervention cũ
        # =================================================
        high_score, high_intervention = (
            score_service.create_score_and_detect(
                enrollment.enrollment_id,
                assessment_high.assessment_id,
                Decimal("4.00"),
            )
        )

        assert high_score.score == Decimal("4.00")
        assert high_intervention is None

        intervention_repo = InterventionRepository()

        with db.transaction() as connection:
            existing_open = intervention_repo.get_open(
                connection,
                enrollment.enrollment_id,
                subject_id,
            )

        assert existing_open is not None
        assert existing_open.status == InterventionStatus.DETECTED

        # =================================================
        # CASE 3:
        # Xóa rule rồi thử nhập score 2.50.
        #
        # Score được INSERT trước detection.
        # Detection phải raise MissingSupportRuleError.
        #
        # Vì cùng transaction nên score vừa INSERT
        # phải bị ROLLBACK hoàn toàn.
        # =================================================
        with db.transaction() as connection:
            connection.cursor().execute(
                """
                DELETE FROM SUPPORT_RULES
                WHERE subject_id = ?
                  AND school_year_id = ?
                """,
                subject_id,
                school_year_id,
            )

        with pytest.raises(MissingSupportRuleError):
            score_service.create_score_and_detect(
                enrollment.enrollment_id,
                assessment_rollback.assessment_id,
                Decimal("2.50"),
            )

        # Kiểm tra score rollback thật sự
        with db.transaction() as connection:
            rolled_back_score = (
                score_service.score_repository
                .get_by_enrollment_assessment(
                    connection,
                    enrollment.enrollment_id,
                    assessment_rollback.assessment_id,
                )
            )

        assert rolled_back_score is None

    finally:
        cleanup(db)
