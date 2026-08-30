from config.database import db_settings
from database.connection import DatabaseManager
from models.enums import UserRole
from repositories import UserRepository


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
            DELETE FROM dbo.USERS
            WHERE username LIKE 'test_repo_%'
            """
        )


def test_user_repository_flow():
    test_db = get_test_db()
    repo = UserRepository()

    cleanup(test_db)

    with test_db.transaction() as connection:
        user = repo.create(
            connection=connection,
            username="test_repo_admin",
            password_hash="$2b$12$fakehashfortestonly",
            full_name="Admin Repository Test",
            role=UserRole.ADMIN,
            email="admin.test@example.com",
            phone="0900000001",
        )

        assert user.user_id > 0
        assert user.username == "test_repo_admin"
        assert user.role == UserRole.ADMIN
        assert user.is_active is True

        user_id = user.user_id

    with test_db.transaction() as connection:
        found = repo.get_by_username(
            connection,
            "test_repo_admin",
        )

        assert found is not None
        assert found.user_id == user_id

    with test_db.transaction() as connection:
        updated = repo.update_profile(
            connection,
            user_id,
            "Admin Test Updated",
            "updated@example.com",
            "0911111111",
        )

        assert updated is not None
        assert updated.full_name == "Admin Test Updated"
        assert updated.phone == "0911111111"

    with test_db.transaction() as connection:
        password_updated = repo.update_password_hash(
            connection,
            user_id,
            "$2b$12$newfakehashfortestonly",
        )

        assert password_updated is not None
        assert (
            password_updated.password_hash
            == "$2b$12$newfakehashfortestonly"
        )

    with test_db.transaction() as connection:
        inactive = repo.set_active(
            connection,
            user_id,
            False,
        )

        assert inactive is not None
        assert inactive.is_active is False

    with test_db.transaction() as connection:
        users = repo.list_all(connection)

        assert any(
            user.user_id == user_id
            for user in users
        )

    cleanup(test_db)