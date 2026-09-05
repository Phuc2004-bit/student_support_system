from datetime import date

import pyodbc

from models.dto import (
    Student,
    StudentCreateData,
    StudentUpdateData,
)
from models.enums import StudentStatus


class StudentRepository:
    def create(
        self,
        connection: pyodbc.Connection,
        student_id: str,
        data: StudentCreateData,
    ) -> Student:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO dbo.STUDENTS
            (
                student_id,
                student_code,
                full_name,
                date_of_birth,
                gender,
                phone,
                email,
                address,
                status
            )
            OUTPUT
                INSERTED.student_id,
                INSERTED.student_code,
                INSERTED.full_name,
                INSERTED.date_of_birth,
                INSERTED.gender,
                INSERTED.phone,
                INSERTED.email,
                INSERTED.address,
                INSERTED.status,
                INSERTED.created_at,
                INSERTED.updated_at
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            student_id,
            data.student_code,
            data.full_name,
            data.date_of_birth,
            data.gender,
            data.phone,
            data.email,
            data.address,
            StudentStatus.ACTIVE.value,
        )

        row = cursor.fetchone()

        return self._map_student(row)

    def get_by_id(
        self,
        connection: pyodbc.Connection,
        student_id: str,
    ) -> Student | None:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                student_id,
                student_code,
                full_name,
                date_of_birth,
                gender,
                phone,
                email,
                address,
                status,
                created_at,
                updated_at
            FROM dbo.STUDENTS
            WHERE student_id = ?
            """,
            student_id,
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return self._map_student(row)

    def get_by_code(
        self,
        connection: pyodbc.Connection,
        student_code: str,
    ) -> Student | None:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                student_id,
                student_code,
                full_name,
                date_of_birth,
                gender,
                phone,
                email,
                address,
                status,
                created_at,
                updated_at
            FROM dbo.STUDENTS
            WHERE student_code = ?
            """,
            student_code,
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return self._map_student(row)

    def list_all(
        self,
        connection: pyodbc.Connection,
    ) -> list[Student]:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                student_id,
                student_code,
                full_name,
                date_of_birth,
                gender,
                phone,
                email,
                address,
                status,
                created_at,
                updated_at
            FROM dbo.STUDENTS
            ORDER BY full_name, student_code
            """
        )

        return [
            self._map_student(row)
            for row in cursor.fetchall()
        ]

    def list_by_ids(
        self,
        connection: pyodbc.Connection,
        student_ids: tuple[str, ...],
    ) -> list[Student]:
        if not student_ids:
            return []
        placeholders = ", ".join("?" for _ in student_ids)
        cursor = connection.cursor()
        cursor.execute(
            f"""
            SELECT
                student_id,
                student_code,
                full_name,
                date_of_birth,
                gender,
                phone,
                email,
                address,
                status,
                created_at,
                updated_at
            FROM dbo.STUDENTS
            WHERE student_id IN ({placeholders})
            ORDER BY student_id
            """,
            *student_ids,
        )
        return [self._map_student(row) for row in cursor.fetchall()]

    def update(
        self,
        connection: pyodbc.Connection,
        student_id: str,
        data: StudentUpdateData,
    ) -> Student | None:
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE dbo.STUDENTS
            SET
                full_name = ?,
                date_of_birth = ?,
                gender = ?,
                phone = ?,
                email = ?,
                address = ?,
                updated_at = GETDATE()
            OUTPUT
                INSERTED.student_id,
                INSERTED.student_code,
                INSERTED.full_name,
                INSERTED.date_of_birth,
                INSERTED.gender,
                INSERTED.phone,
                INSERTED.email,
                INSERTED.address,
                INSERTED.status,
                INSERTED.created_at,
                INSERTED.updated_at
            WHERE student_id = ?
            """,
            data.full_name,
            data.date_of_birth,
            data.gender,
            data.phone,
            data.email,
            data.address,
            student_id,
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return self._map_student(row)

    def set_status(
        self,
        connection: pyodbc.Connection,
        student_id: str,
        status: StudentStatus,
    ) -> Student | None:
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE dbo.STUDENTS
            SET
                status = ?,
                updated_at = GETDATE()
            OUTPUT
                INSERTED.student_id,
                INSERTED.student_code,
                INSERTED.full_name,
                INSERTED.date_of_birth,
                INSERTED.gender,
                INSERTED.phone,
                INSERTED.email,
                INSERTED.address,
                INSERTED.status,
                INSERTED.created_at,
                INSERTED.updated_at
            WHERE student_id = ?
            """,
            status.value,
            student_id,
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return self._map_student(row)

    @staticmethod
    def _map_student(row) -> Student:
        return Student(
            student_id=row.student_id,
            student_code=row.student_code,
            full_name=row.full_name,
            date_of_birth=row.date_of_birth,
            gender=row.gender,
            phone=row.phone,
            email=row.email,
            address=row.address,
            status=StudentStatus(row.status),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
