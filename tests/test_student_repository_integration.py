from datetime import date

from config.database import db_settings
from database.connection import DatabaseManager
from models.dto import (
    StudentCreateData,
    StudentUpdateData,
)
from models.enums import StudentStatus
from repositories import StudentRepository


def get_test_db() -> DatabaseManager:
    connection_string = db_settings.connection_string().replace(
        "DATABASE=student_support_db;",
        "DATABASE=student_support_db_test;",
    )

    return DatabaseManager(connection_string)


def cleanup_students(test_db: DatabaseManager) -> None:
    with test_db.transaction() as connection:
        cursor = connection.cursor()

        cursor.execute(
            """
            DELETE FROM dbo.STUDENTS
            WHERE student_code LIKE 'TEST_%'
            """
        )


def test_student_repository_crud():
    test_db = get_test_db()
    repository = StudentRepository()

    cleanup_students(test_db)

    student_id = "test-student-001"

    create_data = StudentCreateData(
        student_code="TEST_HS001",
        full_name="Nguyễn Văn Test",
        date_of_birth=date(2010, 5, 20),
        gender="Nam",
        phone="0900000000",
        email="test@example.com",
        address="Hà Nội",
    )

    with test_db.transaction() as connection:
        created = repository.create(
            connection,
            student_id,
            create_data,
        )

        assert created.student_id == student_id
        assert created.student_code == "TEST_HS001"
        assert created.status == StudentStatus.ACTIVE

    with test_db.transaction() as connection:
        found = repository.get_by_id(
            connection,
            student_id,
        )

        assert found is not None
        assert found.full_name == "Nguyễn Văn Test"

    with test_db.transaction() as connection:
        found_by_code = repository.get_by_code(
            connection,
            "TEST_HS001",
        )

        assert found_by_code is not None
        assert found_by_code.student_id == student_id

    update_data = StudentUpdateData(
        full_name="Nguyễn Văn Test Updated",
        date_of_birth=date(2010, 5, 20),
        gender="Nam",
        phone="0911111111",
        email="updated@example.com",
        address="Hà Nội",
    )

    with test_db.transaction() as connection:
        updated = repository.update(
            connection,
            student_id,
            update_data,
        )

        assert updated is not None
        assert updated.full_name == "Nguyễn Văn Test Updated"
        assert updated.phone == "0911111111"

    with test_db.transaction() as connection:
        inactive = repository.set_status(
            connection,
            student_id,
            StudentStatus.INACTIVE,
        )

        assert inactive is not None
        assert inactive.status == StudentStatus.INACTIVE

    with test_db.transaction() as connection:
        students = repository.list_all(connection)

        assert any(
            student.student_id == student_id
            for student in students
        )

    cleanup_students(test_db)