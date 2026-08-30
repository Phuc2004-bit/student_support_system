from database.connection import DatabaseManager
from config.database import db_settings


def get_test_connection_string() -> str:
    return db_settings.connection_string().replace(
        "DATABASE=student_support_db;",
        "DATABASE=student_support_db_test;",
    )


def test_commit():
    test_db = DatabaseManager(
        get_test_connection_string()
    )

    with test_db.transaction() as conn:
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO dbo.TRANSACTION_TEST (test_value)
            VALUES (?)
            """,
            "COMMIT_OK",
        )

    print("COMMIT TEST: OK")


def test_rollback():
    test_db = DatabaseManager(
        get_test_connection_string()
    )

    try:
        with test_db.transaction() as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO dbo.TRANSACTION_TEST (test_value)
                VALUES (?)
                """,
                "ROLLBACK_TEST",
            )

            # Giả lập lỗi xảy ra giữa transaction
            raise RuntimeError(
                "Simulated transaction failure"
            )

    except RuntimeError:
        print("ROLLBACK TRIGGERED: OK")


def show_results():
    test_db = DatabaseManager(
        get_test_connection_string()
    )

    conn = test_db.get_connection()

    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, test_value
            FROM dbo.TRANSACTION_TEST
            ORDER BY id
            """
        )

        rows = cursor.fetchall()

        print("\nDATA AFTER TEST:")

        for row in rows:
            print(row.id, row.test_value)

    finally:
        conn.close()


def main():
    test_commit()
    test_rollback()
    show_results()


if __name__ == "__main__":
    main()