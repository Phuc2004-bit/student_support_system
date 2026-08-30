from config.database import db_settings
from database.connection import DatabaseManager


TABLE_NAME = "dbo.TRANSACTION_TEST"


def get_test_connection_string() -> str:
    return db_settings.connection_string().replace(
        "DATABASE=student_support_db;",
        "DATABASE=student_support_db_test;",
    )


def create_test_table(test_db: DatabaseManager) -> None:
    with test_db.transaction() as conn:
        cursor = conn.cursor()

        cursor.execute(
            f"""
            IF OBJECT_ID('{TABLE_NAME}', 'U') IS NOT NULL
                DROP TABLE {TABLE_NAME};

            CREATE TABLE {TABLE_NAME}
            (
                id INT IDENTITY(1,1) PRIMARY KEY,
                test_value VARCHAR(100) NOT NULL
            );
            """
        )


def drop_test_table(test_db: DatabaseManager) -> None:
    with test_db.transaction() as conn:
        cursor = conn.cursor()

        cursor.execute(
            f"""
            IF OBJECT_ID('{TABLE_NAME}', 'U') IS NOT NULL
                DROP TABLE {TABLE_NAME};
            """
        )


def test_commit():
    test_db = DatabaseManager(
        get_test_connection_string()
    )

    create_test_table(test_db)

    try:
        with test_db.transaction() as conn:
            cursor = conn.cursor()

            cursor.execute(
                f"""
                INSERT INTO {TABLE_NAME} (test_value)
                VALUES (?)
                """,
                "COMMIT_OK",
            )

        with test_db.transaction() as conn:
            cursor = conn.cursor()

            cursor.execute(
                f"""
                SELECT COUNT(*)
                FROM {TABLE_NAME}
                WHERE test_value = ?
                """,
                "COMMIT_OK",
            )

            count = cursor.fetchone()[0]

        assert count == 1

    finally:
        drop_test_table(test_db)


def test_rollback():
    test_db = DatabaseManager(
        get_test_connection_string()
    )

    create_test_table(test_db)

    try:
        try:
            with test_db.transaction() as conn:
                cursor = conn.cursor()

                cursor.execute(
                    f"""
                    INSERT INTO {TABLE_NAME} (test_value)
                    VALUES (?)
                    """,
                    "ROLLBACK_TEST",
                )

                raise RuntimeError(
                    "Simulated error for rollback test"
                )

        except RuntimeError:
            pass

        with test_db.transaction() as conn:
            cursor = conn.cursor()

            cursor.execute(
                f"""
                SELECT COUNT(*)
                FROM {TABLE_NAME}
                WHERE test_value = ?
                """,
                "ROLLBACK_TEST",
            )

            count = cursor.fetchone()[0]

        assert count == 0

    finally:
        drop_test_table(test_db)