import pyodbc

from models.dto import User, UserListItem
from models.enums import UserRole


class UserRepository:
    def create(
        self,
        connection: pyodbc.Connection,
        username: str,
        password_hash: str,
        full_name: str,
        role: UserRole,
        email: str | None = None,
        phone: str | None = None,
        is_active: bool = True,
    ) -> User:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO dbo.USERS
            (
                username,
                password_hash,
                full_name,
                role,
                email,
                phone,
                is_active
            )
            OUTPUT
                INSERTED.user_id,
                INSERTED.username,
                INSERTED.password_hash,
                INSERTED.full_name,
                INSERTED.role,
                INSERTED.email,
                INSERTED.phone,
                INSERTED.is_active,
                INSERTED.created_at,
                INSERTED.updated_at
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            username,
            password_hash,
            full_name,
            role.value,
            email,
            phone,
            int(is_active),
        )

        return self._map_user(cursor.fetchone())

    def get_by_id(
        self,
        connection: pyodbc.Connection,
        user_id: int,
    ) -> User | None:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                user_id,
                username,
                password_hash,
                full_name,
                role,
                email,
                phone,
                is_active,
                created_at,
                updated_at
            FROM dbo.USERS
            WHERE user_id = ?
            """,
            user_id,
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return self._map_user(row)

    def get_by_username(
        self,
        connection: pyodbc.Connection,
        username: str,
    ) -> User | None:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                user_id,
                username,
                password_hash,
                full_name,
                role,
                email,
                phone,
                is_active,
                created_at,
                updated_at
            FROM dbo.USERS
            WHERE username = ?
            """,
            username,
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return self._map_user(row)

    def list_all(
        self,
        connection: pyodbc.Connection,
    ) -> list[User]:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                user_id,
                username,
                password_hash,
                full_name,
                role,
                email,
                phone,
                is_active,
                created_at,
                updated_at
            FROM dbo.USERS
            ORDER BY full_name, username
            """
        )

        return [
            self._map_user(row)
            for row in cursor.fetchall()
        ]

    def list_for_management(
        self,
        connection: pyodbc.Connection,
        search: str | None = None,
    ) -> list[UserListItem]:
        conditions = ""
        parameters: list[object] = []
        if search is not None:
            conditions = "WHERE username LIKE ? OR full_name LIKE ?"
            pattern = f"%{search}%"
            parameters.extend((pattern, pattern))
        cursor = connection.cursor()
        cursor.execute(
            f"""
            SELECT
                user_id,
                username,
                full_name,
                role,
                email,
                phone,
                is_active,
                created_at,
                updated_at
            FROM dbo.USERS
            {conditions}
            ORDER BY full_name, username, user_id
            """,
            *parameters,
        )
        return [self._map_list_item(row) for row in cursor.fetchall()]

    def list_active_teachers(
        self,
        connection: pyodbc.Connection,
    ) -> list[User]:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT
                user_id,
                username,
                password_hash,
                full_name,
                role,
                email,
                phone,
                is_active,
                created_at,
                updated_at
            FROM dbo.USERS
            WHERE role = ?
              AND is_active = ?
            ORDER BY full_name, username
            """,
            UserRole.TEACHER.value,
            1,
        )
        return [self._map_user(row) for row in cursor.fetchall()]

    def set_active(
        self,
        connection: pyodbc.Connection,
        user_id: int,
        is_active: bool,
    ) -> User | None:
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE dbo.USERS
            SET
                is_active = ?,
                updated_at = GETDATE()
            OUTPUT
                INSERTED.user_id,
                INSERTED.username,
                INSERTED.password_hash,
                INSERTED.full_name,
                INSERTED.role,
                INSERTED.email,
                INSERTED.phone,
                INSERTED.is_active,
                INSERTED.created_at,
                INSERTED.updated_at
            WHERE user_id = ?
            """,
            int(is_active),
            user_id,
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return self._map_user(row)

    def update_profile(
        self,
        connection: pyodbc.Connection,
        user_id: int,
        full_name: str,
        email: str | None,
        phone: str | None,
    ) -> User | None:
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE dbo.USERS
            SET
                full_name = ?,
                email = ?,
                phone = ?,
                updated_at = GETDATE()
            OUTPUT
                INSERTED.user_id,
                INSERTED.username,
                INSERTED.password_hash,
                INSERTED.full_name,
                INSERTED.role,
                INSERTED.email,
                INSERTED.phone,
                INSERTED.is_active,
                INSERTED.created_at,
                INSERTED.updated_at
            WHERE user_id = ?
            """,
            full_name,
            email,
            phone,
            user_id,
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return self._map_user(row)

    def get_profile_by_id(
        self,
        connection: pyodbc.Connection,
        user_id: int,
    ) -> UserListItem | None:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT
                user_id,
                username,
                full_name,
                role,
                email,
                phone,
                is_active,
                created_at,
                updated_at
            FROM dbo.USERS
            WHERE user_id = ?
            """,
            user_id,
        )
        row = cursor.fetchone()
        return None if row is None else self._map_list_item(row)

    def update_management_details(
        self,
        connection: pyodbc.Connection,
        user_id: int,
        full_name: str,
        role: UserRole,
        email: str | None,
        phone: str | None,
    ) -> User | None:
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE dbo.USERS
            SET
                full_name = ?,
                role = ?,
                email = ?,
                phone = ?,
                updated_at = GETDATE()
            OUTPUT
                INSERTED.user_id,
                INSERTED.username,
                INSERTED.password_hash,
                INSERTED.full_name,
                INSERTED.role,
                INSERTED.email,
                INSERTED.phone,
                INSERTED.is_active,
                INSERTED.created_at,
                INSERTED.updated_at
            WHERE user_id = ?
            """,
            full_name,
            role.value,
            email,
            phone,
            user_id,
        )
        row = cursor.fetchone()
        return None if row is None else self._map_user(row)

    def count_active_admins(
        self,
        connection: pyodbc.Connection,
    ) -> int:
        row = connection.cursor().execute(
            """
            SELECT COUNT(*)
            FROM dbo.USERS
            WHERE role = ?
              AND is_active = ?
            """,
            UserRole.ADMIN.value,
            1,
        ).fetchone()
        return int(row[0])

    def update_password_hash(
        self,
        connection: pyodbc.Connection,
        user_id: int,
        password_hash: str,
    ) -> User | None:
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE dbo.USERS
            SET
                password_hash = ?,
                updated_at = GETDATE()
            OUTPUT
                INSERTED.user_id,
                INSERTED.username,
                INSERTED.password_hash,
                INSERTED.full_name,
                INSERTED.role,
                INSERTED.email,
                INSERTED.phone,
                INSERTED.is_active,
                INSERTED.created_at,
                INSERTED.updated_at
            WHERE user_id = ?
            """,
            password_hash,
            user_id,
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return self._map_user(row)

    @staticmethod
    def _map_user(row) -> User:
        return User(
            user_id=row.user_id,
            username=row.username,
            password_hash=row.password_hash,
            full_name=row.full_name,
            role=UserRole(row.role),
            email=row.email,
            phone=row.phone,
            is_active=bool(row.is_active),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _map_list_item(row) -> UserListItem:
        return UserListItem(
            user_id=int(row[0]),
            username=row[1],
            full_name=row[2],
            role=UserRole(row[3]),
            email=row[4],
            phone=row[5],
            is_active=bool(row[6]),
            created_at=row[7],
            updated_at=row[8],
        )
