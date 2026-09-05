import bcrypt
import pytest

from config.database import db_settings
from database.connection import DatabaseManager
from exceptions import BusinessRuleError, DuplicateError, ValidationError
from models.dto import UserSession
from models.enums import UserRole
from services.auth_service import AuthService
from services.user_service import UserService


USERNAMES = ("t127_actor", "t127_admin", "t127_teacher")
PASSWORD = "T127Password@123"


def require_test_database(connection_string: str) -> str:
    normalized = connection_string.upper().replace(" ", "")
    if "DATABASE=STUDENT_SUPPORT_DB_TEST;" not in normalized:
        raise RuntimeError("Integration writes require student_support_db_test.")
    return connection_string


def get_test_db() -> DatabaseManager:
    connection_string = db_settings.connection_string().replace(
        "DATABASE=student_support_db;",
        "DATABASE=student_support_db_test;",
    )
    return DatabaseManager(require_test_database(connection_string))


def assert_connected_test_database(db: DatabaseManager) -> None:
    require_test_database(db.connection_string)
    connection = db.get_connection()
    try:
        actual = connection.cursor().execute("SELECT DB_NAME()").fetchone()[0]
        assert actual == "student_support_db_test"
    finally:
        connection.rollback()
        connection.close()


def cleanup(db: DatabaseManager) -> None:
    assert_connected_test_database(db)
    with db.transaction() as connection:
        connection.cursor().execute(
            "DELETE FROM dbo.USERS WHERE username IN (?, ?, ?)",
            *USERNAMES,
        )


def test_user_management_guard_rejects_production_before_write():
    with pytest.raises(RuntimeError):
        require_test_database(
            "SERVER=.\\SQLEXPRESS;DATABASE=student_support_db;Trusted_Connection=yes;"
        )


def test_admin_user_management_and_auth_lifecycle_against_test_database():
    db = get_test_db()
    assert_connected_test_database(db)
    cleanup(db)
    users = UserService(db)
    auth = AuthService(db)

    try:
        actor_user = users.create_user(
            USERNAMES[0],
            PASSWORD,
            "T127 Actor",
            UserRole.ADMIN,
        )
        actor = auth.login(USERNAMES[0], PASSWORD)
        assert actor == UserSession(
            actor_user.user_id,
            USERNAMES[0],
            "T127 Actor",
            UserRole.ADMIN,
        )

        created_admin = users.admin_create_user(
            actor,
            f"  {USERNAMES[1].upper()}  ",
            PASSWORD,
            "  T127 Admin  ",
            UserRole.ADMIN,
            "t127.admin@example.com",
            None,
            True,
        )
        created_teacher = users.admin_create_user(
            actor,
            USERNAMES[2],
            PASSWORD,
            "T127 Teacher",
            UserRole.TEACHER,
            None,
            "0901234567",
            True,
        )

        assert created_admin.role == UserRole.ADMIN
        assert created_teacher.role == UserRole.TEACHER
        assert created_teacher.password_hash != PASSWORD
        assert created_teacher.password_hash.startswith("$2")
        assert bcrypt.checkpw(
            PASSWORD.encode("utf-8"),
            created_teacher.password_hash.encode("utf-8"),
        )

        listed = users.admin_list_users(actor, "T127_")
        listed_names = {entry.username for entry in listed}
        assert set(USERNAMES) <= listed_names
        assert all(not hasattr(entry, "password_hash") for entry in listed)

        with pytest.raises(DuplicateError):
            users.admin_create_user(
                actor,
                USERNAMES[2].upper(),
                PASSWORD,
                "Duplicate",
                UserRole.TEACHER,
            )

        updated = users.admin_update_user(
            actor,
            created_teacher.user_id,
            "  T127 Teacher Updated  ",
            UserRole.ADMIN,
            "teacher.updated@example.com",
            None,
        )
        assert updated.username == USERNAMES[2]
        assert updated.password_hash == created_teacher.password_hash
        assert updated.full_name == "T127 Teacher Updated"
        assert updated.role == UserRole.ADMIN

        disabled = users.admin_set_user_active(actor, created_teacher.user_id, False)
        assert disabled.is_active is False
        with pytest.raises(ValidationError):
            auth.login(USERNAMES[2], PASSWORD)

        users.admin_set_user_active(actor, created_teacher.user_id, True)
        relogged = auth.login(USERNAMES[2], PASSWORD)
        assert relogged.user_id == created_teacher.user_id
        assert relogged.role == UserRole.ADMIN

        with pytest.raises(BusinessRuleError):
            users.admin_set_user_active(actor, actor.user_id, False)

        teacher_actor = UserSession(
            created_admin.user_id,
            created_admin.username,
            created_admin.full_name,
            UserRole.TEACHER,
        )
        with pytest.raises(ValidationError):
            users.admin_list_users(teacher_actor)
    finally:
        cleanup(db)
