from datetime import date

from config.database import db_settings
from database.connection import DatabaseManager
from models.dto import StudentCreateData
from models.enums import EnrollmentStatus
from repositories import (
    EnrollmentRepository,
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
            DELETE FROM dbo.STUDENT_ENROLLMENTS
            WHERE student_id = 'test-enroll-student'
            """
        )

        cursor.execute(
            """
            DELETE FROM dbo.STUDENTS
            WHERE student_id = 'test-enroll-student'
            """
        )

        cursor.execute(
            """
            DELETE FROM dbo.CLASSES
            WHERE class_name = N'TEST_10A1'
            """
        )

        cursor.execute(
            """
            DELETE FROM dbo.SCHOOL_YEARS
            WHERE year_name = 'TEST_2026_2027'
            """
        )


def test_enrollment_repository_flow():
    test_db = get_test_db()

    student_repo = StudentRepository()
    enrollment_repo = EnrollmentRepository()

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

        cursor.execute(
            """
            INSERT INTO dbo.SCHOOL_YEARS
            (
                year_name,
                start_date,
                end_date,
                is_current
            )
            OUTPUT INSERTED.school_year_id
            VALUES (?, ?, ?, ?)
            """,
            "TEST_2026_2027",
            date(2026, 9, 7),
            date(2027, 5, 31),
            0,
        )

        school_year_id = cursor.fetchone()[0]

        cursor.execute(
            """
            INSERT INTO dbo.CLASSES
            (
                class_name,
                grade_id,
                school_year_id,
                homeroom_teacher,
                status
            )
            OUTPUT INSERTED.class_id
            VALUES (?, ?, ?, ?, ?)
            """,
            "TEST_10A1",
            grade_id,
            school_year_id,
            None,
            "ACTIVE",
        )

        class_id = cursor.fetchone()[0]

        student_repo.create(
            connection,
            "test-enroll-student",
            StudentCreateData(
                student_code="TEST_ENROLL_001",
                full_name="Học sinh Enrollment Test",
            ),
        )

        enrollment = enrollment_repo.create(
            connection,
            "test-enroll-student",
            class_id,
            date(2026, 9, 7),
        )

        assert enrollment.status == EnrollmentStatus.ACTIVE

        enrollment_id = enrollment.enrollment_id

    with test_db.transaction() as connection:
        active = enrollment_repo.get_active_by_student(
            connection,
            "test-enroll-student",
        )

        assert active is not None
        assert active.enrollment_id == enrollment_id

    with test_db.transaction() as connection:
        history = enrollment_repo.list_by_student(
            connection,
            "test-enroll-student",
        )

        assert len(history) == 1
        assert history[0].class_name == "TEST_10A1"
        assert history[0].grade_number == 10
        assert history[0].school_year_name == "TEST_2026_2027"

    with test_db.transaction() as connection:
        transferred = enrollment_repo.set_status(
            connection,
            enrollment_id,
            EnrollmentStatus.TRANSFERRED,
        )

        assert transferred is not None
        assert transferred.status == EnrollmentStatus.TRANSFERRED

    cleanup(test_db)