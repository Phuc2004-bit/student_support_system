import pyodbc

from models.dto import (
    Enrollment,
    EnrollmentListItem,
)
from models.enums import EnrollmentStatus


class EnrollmentRepository:
    def create(
        self,
        connection: pyodbc.Connection,
        student_id: str,
        class_id: int,
        enrollment_date,
    ) -> Enrollment:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO dbo.STUDENT_ENROLLMENTS
            (
                student_id,
                class_id,
                enrollment_date,
                status
            )
            OUTPUT
                INSERTED.enrollment_id,
                INSERTED.student_id,
                INSERTED.class_id,
                INSERTED.enrollment_date,
                INSERTED.status,
                INSERTED.created_at
            VALUES (?, ?, ?, ?)
            """,
            student_id,
            class_id,
            enrollment_date,
            EnrollmentStatus.ACTIVE.value,
        )

        row = cursor.fetchone()

        return self._map_enrollment(row)

    def get_by_id(
        self,
        connection: pyodbc.Connection,
        enrollment_id: int,
    ) -> Enrollment | None:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                enrollment_id,
                student_id,
                class_id,
                enrollment_date,
                status,
                created_at
            FROM dbo.STUDENT_ENROLLMENTS
            WHERE enrollment_id = ?
            """,
            enrollment_id,
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return self._map_enrollment(row)

    def list_by_student(
        self,
        connection: pyodbc.Connection,
        student_id: str,
    ) -> list[EnrollmentListItem]:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                e.enrollment_id,
                e.student_id,
                s.student_code,
                s.full_name,
                e.class_id,
                c.class_name,
                g.grade_number,
                sy.school_year_id,
                sy.year_name AS school_year_name,
                e.status
            FROM dbo.STUDENT_ENROLLMENTS e
            INNER JOIN dbo.STUDENTS s
                ON s.student_id = e.student_id
            INNER JOIN dbo.CLASSES c
                ON c.class_id = e.class_id
            INNER JOIN dbo.GRADES g
                ON g.grade_id = c.grade_id
            INNER JOIN dbo.SCHOOL_YEARS sy
                ON sy.school_year_id = c.school_year_id
            WHERE e.student_id = ?
            ORDER BY sy.start_date, c.class_name
            """,
            student_id,
        )

        return [
            self._map_list_item(row)
            for row in cursor.fetchall()
        ]

    def get_active_by_student(
        self,
        connection: pyodbc.Connection,
        student_id: str,
    ) -> Enrollment | None:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                enrollment_id,
                student_id,
                class_id,
                enrollment_date,
                status,
                created_at
            FROM dbo.STUDENT_ENROLLMENTS
            WHERE student_id = ?
              AND status = ?
            ORDER BY enrollment_id DESC
            """,
            student_id,
            EnrollmentStatus.ACTIVE.value,
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return self._map_enrollment(row)

    def list_by_class(
        self,
        connection: pyodbc.Connection,
        class_id: int,
        school_year_id: int,
        status: EnrollmentStatus | None = None,
    ) -> list[EnrollmentListItem]:
        cursor = connection.cursor()
        parameters: list[object] = [
            class_id,
            school_year_id,
        ]
        status_filter = ""

        if status is not None:
            status_filter = "AND e.status = ?"
            parameters.append(status.value)

        cursor.execute(
            f"""
            SELECT
                e.enrollment_id,
                e.student_id,
                s.student_code,
                s.full_name,
                e.class_id,
                c.class_name,
                g.grade_number,
                sy.school_year_id,
                sy.year_name AS school_year_name,
                e.status
            FROM dbo.STUDENT_ENROLLMENTS e
            INNER JOIN dbo.STUDENTS s
                ON s.student_id = e.student_id
            INNER JOIN dbo.CLASSES c
                ON c.class_id = e.class_id
            INNER JOIN dbo.GRADES g
                ON g.grade_id = c.grade_id
            INNER JOIN dbo.SCHOOL_YEARS sy
                ON sy.school_year_id = c.school_year_id
            WHERE e.class_id = ?
              AND c.school_year_id = ?
              {status_filter}
            ORDER BY
                s.full_name,
                s.student_code,
                e.enrollment_id
            """,
            *parameters,
        )

        return [
            self._map_list_item(row)
            for row in cursor.fetchall()
        ]

    def list_by_student_ids(
        self,
        connection: pyodbc.Connection,
        student_ids: tuple[str, ...],
    ) -> list[EnrollmentListItem]:
        if not student_ids:
            return []
        placeholders = ", ".join("?" for _ in student_ids)
        cursor = connection.cursor()
        cursor.execute(
            f"""
            SELECT
                e.enrollment_id,
                e.student_id,
                s.student_code,
                s.full_name,
                e.class_id,
                c.class_name,
                g.grade_number,
                sy.school_year_id,
                sy.year_name AS school_year_name,
                e.status
            FROM dbo.STUDENT_ENROLLMENTS e
            INNER JOIN dbo.STUDENTS s
                ON s.student_id = e.student_id
            INNER JOIN dbo.CLASSES c
                ON c.class_id = e.class_id
            INNER JOIN dbo.GRADES g
                ON g.grade_id = c.grade_id
            INNER JOIN dbo.SCHOOL_YEARS sy
                ON sy.school_year_id = c.school_year_id
            WHERE e.student_id IN ({placeholders})
            ORDER BY e.student_id, sy.start_date, e.enrollment_id
            """,
            *student_ids,
        )
        return [self._map_list_item(row) for row in cursor.fetchall()]

    def set_status(
        self,
        connection: pyodbc.Connection,
        enrollment_id: int,
        status: EnrollmentStatus,
    ) -> Enrollment | None:
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE dbo.STUDENT_ENROLLMENTS
            SET status = ?
            OUTPUT
                INSERTED.enrollment_id,
                INSERTED.student_id,
                INSERTED.class_id,
                INSERTED.enrollment_date,
                INSERTED.status,
                INSERTED.created_at
            WHERE enrollment_id = ?
            """,
            status.value,
            enrollment_id,
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return self._map_enrollment(row)

    @staticmethod
    def _map_enrollment(row) -> Enrollment:
        return Enrollment(
            enrollment_id=row.enrollment_id,
            student_id=row.student_id,
            class_id=row.class_id,
            enrollment_date=row.enrollment_date,
            status=EnrollmentStatus(row.status),
            created_at=row.created_at,
        )

    @staticmethod
    def _map_list_item(row) -> EnrollmentListItem:
        return EnrollmentListItem(
            enrollment_id=row.enrollment_id,
            student_id=row.student_id,
            student_code=row.student_code,
            full_name=row.full_name,
            class_id=row.class_id,
            class_name=row.class_name,
            grade_number=row.grade_number,
            school_year_id=row.school_year_id,
            school_year_name=row.school_year_name,
            status=EnrollmentStatus(row.status),
        )
