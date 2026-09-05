import bcrypt
import pytest

from config.database import db_settings
from database.connection import DatabaseManager
from exceptions import BusinessRuleError, ValidationError
from models.enums import UserRole
from services.auth_service import AuthService
from services.user_service import UserService


USERNAMES = ("t128_manager", "t128_account")
OLD_PASSWORD = "T128Password@123"
NEW_PASSWORD = "T128Different@456"


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
            "DELETE FROM dbo.USERS WHERE username IN (?, ?)",
            *USERNAMES,
        )


def test_account_guard_rejects_production_before_write():
    with pytest.raises(RuntimeError):
        require_test_database(
            "SERVER=.\\SQLEXPRESS;DATABASE=student_support_db;Trusted_Connection=yes;"
        )


def test_profile_password_session_and_activation_lifecycle_on_test_database():
    db = get_test_db()
    assert_connected_test_database(db)
    cleanup(db)
    users = UserService(db)
    auth = AuthService(db)

    try:
        manager_user = users.create_user(
            USERNAMES[0], OLD_PASSWORD, "T128 Manager", UserRole.ADMIN
        )
        account_user = users.create_user(
            USERNAMES[1], OLD_PASSWORD, "T128 Account", UserRole.TEACHER
        )
        manager = auth.login(USERNAMES[0], OLD_PASSWORD)
        account_session = auth.login(USERNAMES[1], OLD_PASSWORD)

        own_profile = users.get_own_profile(account_session)
        assert own_profile.user_id == account_user.user_id
        assert own_profile.role == UserRole.TEACHER
        assert not hasattr(own_profile, "password_hash")

        updated = users.update_own_profile(
            account_session,
            "  T128 Account Updated  ",
            " account.updated@example.com ",
            " 0901234567 ",
        )
        assert updated.full_name == "T128 Account Updated"
        assert updated.email == "account.updated@example.com"
        assert updated.phone == "0901234567"
        assert updated.username == USERNAMES[1]
        assert updated.role == UserRole.TEACHER
        assert updated.is_active is True
        assert account_session.full_name == "T128 Account"

        with pytest.raises(ValidationError):
            users.change_own_password(
                account_session, "WrongPassword@123", NEW_PASSWORD
            )
        unchanged = users.get_by_username(USERNAMES[1])
        assert bcrypt.checkpw(
            OLD_PASSWORD.encode("utf-8"),
            unchanged.password_hash.encode("utf-8"),
        )

        changed = users.change_own_password(
            account_session, OLD_PASSWORD, NEW_PASSWORD
        )
        assert not hasattr(changed, "password_hash")
        persisted = users.get_by_username(USERNAMES[1])
        assert persisted.password_hash != OLD_PASSWORD
        assert persisted.password_hash != NEW_PASSWORD
        assert bcrypt.checkpw(
            NEW_PASSWORD.encode("utf-8"),
            persisted.password_hash.encode("utf-8"),
        )
        assert users.get_own_profile(account_session).user_id == account_user.user_id

        with pytest.raises(ValidationError):
            auth.login(USERNAMES[1], OLD_PASSWORD)
        relogged = auth.login(USERNAMES[1], NEW_PASSWORD)
        assert relogged.user_id == account_user.user_id
        assert relogged.full_name == "T128 Account Updated"

        with pytest.raises(ValidationError):
            users.admin_list_users(relogged)
        with pytest.raises(BusinessRuleError):
            users.admin_set_user_active(manager, manager_user.user_id, False)

        users.admin_set_user_active(manager, account_user.user_id, False)
        with pytest.raises(ValidationError):
            auth.login(USERNAMES[1], NEW_PASSWORD)
        users.admin_set_user_active(manager, account_user.user_id, True)
        assert auth.login(USERNAMES[1], NEW_PASSWORD).user_id == account_user.user_id

        managed = users.admin_list_users(manager, "t128_")
        assert {entry.username for entry in managed} == set(USERNAMES)
        assert all(not hasattr(entry, "password_hash") for entry in managed)
    finally:
        cleanup(db)
