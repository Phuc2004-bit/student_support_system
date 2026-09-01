import pytest

from config.database import db_settings
from database.connection import DatabaseManager
from exceptions import ValidationError
from models.enums import UserRole
from services import AuthService, UserService


TEST_USERNAME = "auth_teacher_test"
TEST_PASSWORD = "Teacher@123"


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


def test_auth_service_login_flow():
    db = get_test_db()
    cleanup(db)

    try:
        user_service = UserService(db)
        auth_service = AuthService(db)

        # =================================================
        # SEED USER
        # =================================================
        user = user_service.create_user(
            username=TEST_USERNAME,
            password=TEST_PASSWORD,
            full_name="Giáo Viên Auth Test",
            role=UserRole.TEACHER,
            email="auth.teacher@example.com",
            phone="0901234567",
            is_active=True,
        )

        # =================================================
        # CASE 1:
        # Đúng username + đúng password
        # => trả UserSession
        # =================================================
        session = auth_service.login(
            TEST_USERNAME.upper(),
            TEST_PASSWORD,
        )

        assert session.user_id == user.user_id
        assert session.username == TEST_USERNAME
        assert session.full_name == "Giáo Viên Auth Test"
        assert session.role == UserRole.TEACHER

        # UserSession không được chứa password_hash
        assert not hasattr(session, "password_hash")

        # =================================================
        # CASE 2:
        # Đúng username + sai password
        # => ValidationError
        # =================================================
        with pytest.raises(ValidationError):
            auth_service.login(
                TEST_USERNAME,
                "SaiMatKhau@123",
            )

        # =================================================
        # CASE 3:
        # Username không tồn tại
        # => ValidationError
        # =================================================
        with pytest.raises(ValidationError):
            auth_service.login(
                "user_khong_ton_tai",
                TEST_PASSWORD,
            )

        # =================================================
        # CASE 4:
        # Disable tài khoản
        # => không được đăng nhập
        # =================================================
        disabled = user_service.set_active(
            user.user_id,
            False,
        )

        assert disabled.is_active is False

        with pytest.raises(ValidationError):
            auth_service.login(
                TEST_USERNAME,
                TEST_PASSWORD,
            )

        # =================================================
        # CASE 5:
        # Username/password rỗng
        # => ValidationError
        # =================================================
        with pytest.raises(ValidationError):
            auth_service.login(
                "",
                TEST_PASSWORD,
            )

        with pytest.raises(ValidationError):
            auth_service.login(
                TEST_USERNAME,
                "",
            )

    finally:
        cleanup(db)
