from datetime import date

from config.database import db_settings
from database.connection import DatabaseManager
from exceptions import BusinessRuleError
from models.dto import StudentCreateData
from models.enums import EnrollmentStatus
from repositories import AcademicRepository
from services import (
    EnrollmentService,
    StudentService,
)


TEST_CODE = "TEST_ENROLL_SVC_001"


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
            WHERE class_name IN
            (
                N'TEST_SVC_10A1',
                N'TEST_SVC_10A2'
            )
            """
        )

        cursor.execute(
            """
            DELETE FROM dbo.SCHOOL_YEARS
            WHERE year_name = 'TEST_SVC_2026_2027'
            """
        )


def test_enrollment_service_flow():
    test_db = get_test_db()

    student_service = StudentService(test_db)
    enrollment_service = EnrollmentService(test_db)
    academic_repo = AcademicRepository()

    cleanup(test_db)

    try:
        # =============================================
        # SEED ACADEMIC DATA
        # =============================================
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

            school_year_id = (
                academic_repo.create_school_year(
                    connection,
                    "TEST_SVC_2026_2027",
                    date(2026, 9, 7),
                    date(2027, 5, 31),
                    False,
                )
            )

            class_1_id = academic_repo.create_class(
                connection,
                "TEST_SVC_10A1",
                grade_id,
                school_year_id,
            )

            class_2_id = academic_repo.create_class(
                connection,
                "TEST_SVC_10A2",
                grade_id,
                school_year_id,
            )

        # =============================================
        # CREATE STUDENT
        # =============================================
        student = student_service.create_student(
            StudentCreateData(
                student_code=TEST_CODE,
                full_name="Học sinh Enrollment Service",
            )
        )

        student_id = student.student_id

        # =============================================
        # FIRST ENROLLMENT
        # =============================================
        first = enrollment_service.enroll_student(
            student_id,
            class_1_id,
            date(2026, 9, 7),
        )

        assert first.class_id == class_1_id
        assert first.status == EnrollmentStatus.ACTIVE

        first_enrollment_id = first.enrollment_id

        # =============================================
        # CANNOT CREATE SECOND ACTIVE DIRECTLY
        # =============================================
        duplicate_active_blocked = False

        try:
            enrollment_service.enroll_student(
                student_id,
                class_2_id,
                date(2026, 9, 8),
            )
        except BusinessRuleError:
            duplicate_active_blocked = True

        assert duplicate_active_blocked is True

        # =============================================
        # TRANSFER
        # =============================================
        second = enrollment_service.transfer_student(
            student_id,
            class_2_id,
            date(2026, 10, 1),
        )

        assert second.class_id == class_2_id
        assert second.status == EnrollmentStatus.ACTIVE
        assert second.enrollment_id != first_enrollment_id

        # =============================================
        # CURRENT ACTIVE
        # =============================================
        current = (
            enrollment_service.get_active_enrollment(
                student_id
            )
        )

        assert current is not None
        assert current.enrollment_id == second.enrollment_id
        assert current.class_id == class_2_id

        # =============================================
        # HISTORY MUST BE PRESERVED
        # =============================================
        history = (
            enrollment_service.get_student_history(
                student_id
            )
        )

        assert len(history) == 2

        old_record = next(
            item
            for item in history
            if item.enrollment_id == first_enrollment_id
        )

        new_record = next(
            item
            for item in history
            if item.enrollment_id == second.enrollment_id
        )

        assert (
            old_record.status
            == EnrollmentStatus.TRANSFERRED
        )

        assert (
            new_record.status
            == EnrollmentStatus.ACTIVE
        )

    finally:
        cleanup(test_db)