from models.dto import (
    StudentCreateData,
    StudentUpdateData,
)
from models.enums import StudentStatus
from config.database import db_settings
from database.connection import DatabaseManager
from exceptions import DuplicateError
from services import StudentService


TEST_STUDENT_CODE = "TEST_SERVICE_HS001"


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
            DELETE FROM dbo.STUDENTS
            WHERE student_code = ?
            """,
            TEST_STUDENT_CODE,
        )


def test_student_service_flow():
    test_db = get_test_db()
    service = StudentService(test_db)

    cleanup(test_db)

    try:
        # ---------------------------------------------
        # CREATE
        # ---------------------------------------------
        created = service.create_student(
            StudentCreateData(
                student_code=TEST_STUDENT_CODE,
                full_name="Học sinh Service Test",
            )
        )

        assert created.student_code == TEST_STUDENT_CODE
        assert created.full_name == "Học sinh Service Test"
        assert created.status == StudentStatus.ACTIVE

        # student_id phải đúng schema VARCHAR(20)
        assert created.student_id is not None
        assert len(created.student_id) == 20

        student_id = created.student_id

        # ---------------------------------------------
        # READ
        # ---------------------------------------------
        found = service.get_student(student_id)

        assert found.student_id == student_id
        assert found.student_code == TEST_STUDENT_CODE

        found_by_code = service.get_student_by_code(
            TEST_STUDENT_CODE
        )

        assert found_by_code.student_id == student_id

        # ---------------------------------------------
        # DUPLICATE
        # ---------------------------------------------
        duplicate_raised = False

        try:
            service.create_student(
                StudentCreateData(
                    student_code=TEST_STUDENT_CODE,
                    full_name="Học sinh Trùng",
                )
            )
        except DuplicateError:
            duplicate_raised = True

        assert duplicate_raised is True

        # ---------------------------------------------
        # UPDATE
        # ---------------------------------------------
        updated = service.update_student(
            student_id,
            StudentUpdateData(
                full_name="Học sinh Service Updated",
                phone="0912345678",
                email="service.updated@example.com",
            ),
        )

        assert (
            updated.full_name
            == "Học sinh Service Updated"
        )

        assert updated.phone == "0912345678"

        # ---------------------------------------------
        # DEACTIVATE
        # ---------------------------------------------
        inactive = service.deactivate_student(
            student_id
        )

        assert inactive.status == StudentStatus.INACTIVE

        # ---------------------------------------------
        # ACTIVATE
        # ---------------------------------------------
        active = service.activate_student(
            student_id
        )

        assert active.status == StudentStatus.ACTIVE

        # ---------------------------------------------
        # LIST
        # ---------------------------------------------
        students = service.list_students()

        assert any(
            item.student_id == student_id
            for item in students
        )

    finally:
        cleanup(test_db)