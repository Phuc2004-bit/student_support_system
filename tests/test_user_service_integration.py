import bcrypt
import pytest

from config.database import db_settings
from database.connection import DatabaseManager
from exceptions import DuplicateError
from models.enums import UserRole
from services import UserService


TEST_USERNAME = "usr_teacher_test"


def get_test_db() -> DatabaseManager:
    connection_string = db_settings.connection_string().replace(
        "DATABASE=student_support_db;",
        "DATABASE=student_support_db_test;",
    )
    return DatabaseManager(connection_string)


def cleanup(db: DatabaseManager) -> None:
    with db.transaction() as connection:
        connection.cursor().execute(
            """
            DELETE FROM dbo.USERS
            WHERE username = ?
            """,
            TEST_USERNAME,
        )


def test_user_service_full_flow():
    db = get_test_db()
    cleanup(db)

    try:
        service = UserService(db)

        original_password = "Teacher@123"
        new_password = "Teacher@456"

        # 1. CREATE USER
        user = service.create_user(
            username=TEST_USERNAME,
            password=original_password,
            full_name="Giáo Viên Test",
            role=UserRole.TEACHER,
            email="teacher.test@example.com",
            phone="0901234567",
            is_active=True,
        )

        assert user.user_id > 0
        assert user.username == TEST_USERNAME
        assert user.full_name == "Giáo Viên Test"
        assert user.role == UserRole.TEACHER
        assert user.is_active is True

        # 2. PASSWORD MUST BE HASHED
        assert user.password_hash != original_password
        assert user.password_hash.startswith("$2")
        assert bcrypt.checkpw(
            original_password.encode("utf-8"),
            user.password_hash.encode("utf-8"),
        )

        assert service.verify_password(
            original_password,
            user.password_hash,
        ) is True

        assert service.verify_password(
            "SaiMatKhau123",
            user.password_hash,
        ) is False

        # 3. DUPLICATE USERNAME MUST FAIL
        with pytest.raises(DuplicateError):
            service.create_user(
                username=TEST_USERNAME.upper(),
                password="Another@123",
                full_name="Giáo Viên Khác",
                role=UserRole.TEACHER,
            )

        # 4. READ BY ID
        fetched = service.get_user(user.user_id)

        assert fetched.user_id == user.user_id
        assert fetched.username == TEST_USERNAME
        assert fetched.role == UserRole.TEACHER

        # 5. READ BY USERNAME
        fetched_by_username = service.get_by_username(
            TEST_USERNAME.upper()
        )

        assert fetched_by_username is not None
        assert fetched_by_username.user_id == user.user_id

        # 6. UPDATE PROFILE
        updated = service.update_profile(
            user_id=user.user_id,
            full_name="Giáo Viên Test Updated",
            email="teacher.updated@example.com",
            phone="0912345678",
        )

        assert updated.full_name == "Giáo Viên Test Updated"
        assert updated.email == "teacher.updated@example.com"
        assert updated.phone == "0912345678"

        # 7. DISABLE ACCOUNT
        disabled = service.set_active(
            user.user_id,
            False,
        )

        assert disabled.is_active is False

        # 8. RESET PASSWORD
        reset_user = service.reset_password(
            user.user_id,
            new_password,
        )

        assert reset_user.password_hash != original_password
        assert reset_user.password_hash != new_password

        assert service.verify_password(
            original_password,
            reset_user.password_hash,
        ) is False

        assert service.verify_password(
            new_password,
            reset_user.password_hash,
        ) is True

        # 9. LIST USERS
        users = service.list_users()
        matched = [
            item
            for item in users
            if item.username == TEST_USERNAME
        ]

        assert len(matched) == 1
        assert matched[0].user_id == user.user_id

    finally:
        cleanup(db)
