from database.connection import db_manager


def main():
    conn = db_manager.get_connection()

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT DB_NAME()")

        database_name = cursor.fetchone()[0]

        print("Database:", database_name)

    finally:
        conn.close()

    with db_manager.transaction() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1")

        result = cursor.fetchone()[0]

        print("Transaction SELECT:", result)


if __name__ == "__main__":
    main()