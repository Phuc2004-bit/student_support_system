from datetime import date

import pyodbc

from models.dto import Assessment
from models.enums import AssessmentStatus


class AcademicRepository:
    # =====================================================
    # GRADES
    # =====================================================

    def list_grades(
        self,
        connection: pyodbc.Connection,
    ) -> list[tuple[int, int, str | None]]:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                grade_id,
                grade_number,
                grade_name
            FROM dbo.GRADES
            ORDER BY grade_number
            """
        )

        return [
            (
                row.grade_id,
                row.grade_number,
                row.grade_name,
            )
            for row in cursor.fetchall()
        ]

    def get_grade_by_number(
        self,
        connection: pyodbc.Connection,
        grade_number: int,
    ):
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                grade_id,
                grade_number,
                grade_name
            FROM dbo.GRADES
            WHERE grade_number = ?
            """,
            grade_number,
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return (
            row.grade_id,
            row.grade_number,
            row.grade_name,
        )

    # =====================================================
    # SCHOOL YEARS
    # =====================================================

    def create_school_year(
        self,
        connection: pyodbc.Connection,
        year_name: str,
        start_date: date,
        end_date: date,
        is_current: bool = False,
    ) -> int:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO dbo.SCHOOL_YEARS
            (
                year_name,
                start_date,
                end_date,
                is_current
            )
            OUTPUT INSERTED.school_year_id
            VALUES (?, ?, ?, ?)
            """,
            year_name,
            start_date,
            end_date,
            int(is_current),
        )

        return cursor.fetchone()[0]

    def list_school_years(
        self,
        connection: pyodbc.Connection,
    ) -> list[tuple[int, str, date, date, bool]]:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                school_year_id,
                year_name,
                start_date,
                end_date,
                is_current
            FROM dbo.SCHOOL_YEARS
            ORDER BY
                is_current DESC,
                start_date DESC,
                year_name DESC
            """
        )

        return [
            (
                row.school_year_id,
                row.year_name,
                row.start_date,
                row.end_date,
                bool(row.is_current),
            )
            for row in cursor.fetchall()
        ]

    def get_school_year_by_name(
        self,
        connection: pyodbc.Connection,
        year_name: str,
    ):
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                school_year_id,
                year_name,
                start_date,
                end_date,
                is_current
            FROM dbo.SCHOOL_YEARS
            WHERE year_name = ?
            """,
            year_name,
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return (
            row.school_year_id,
            row.year_name,
            row.start_date,
            row.end_date,
            bool(row.is_current),
        )

    # =====================================================
    # CLASSES
    # =====================================================

    def get_class_by_id(
        self,
        connection: pyodbc.Connection,
        class_id: int,
    ):
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                c.class_id,
                c.class_name,
                c.grade_id,
                g.grade_number,
                c.school_year_id,
                sy.year_name AS school_year_name,
                c.homeroom_teacher,
                c.status
            FROM dbo.CLASSES c
            INNER JOIN dbo.GRADES g
                ON g.grade_id = c.grade_id
            INNER JOIN dbo.SCHOOL_YEARS sy
                ON sy.school_year_id = c.school_year_id
            WHERE c.class_id = ?
            """,
            class_id,
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return (
            row.class_id,
            row.class_name,
            row.grade_id,
            row.grade_number,
            row.school_year_id,
            row.school_year_name,
            row.homeroom_teacher,
            row.status,
        )

    def create_class(
        self,
        connection: pyodbc.Connection,
        class_name: str,
        grade_id: int,
        school_year_id: int,
        homeroom_teacher: str | None = None,
        status: str = "ACTIVE",
    ) -> int:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO dbo.CLASSES
            (
                class_name,
                grade_id,
                school_year_id,
                homeroom_teacher,
                status
            )
            OUTPUT INSERTED.class_id
            VALUES (?, ?, ?, ?, ?)
            """,
            class_name,
            grade_id,
            school_year_id,
            homeroom_teacher,
            status,
        )

        return cursor.fetchone()[0]

    def list_classes_by_school_year(
        self,
        connection: pyodbc.Connection,
        school_year_id: int,
    ) -> list[tuple]:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                c.class_id,
                c.class_name,
                g.grade_number,
                c.homeroom_teacher,
                c.status
            FROM dbo.CLASSES c
            INNER JOIN dbo.GRADES g
                ON g.grade_id = c.grade_id
            WHERE c.school_year_id = ?
            ORDER BY
                g.grade_number,
                c.class_name
            """,
            school_year_id,
        )

        return [
            (
                row.class_id,
                row.class_name,
                row.grade_number,
                row.homeroom_teacher,
                row.status,
            )
            for row in cursor.fetchall()
        ]
    

    # =====================================================
    # SUBJECTS
    # =====================================================

    def create_subject(
        self,
        connection: pyodbc.Connection,
        subject_code: str,
        subject_name: str,
        is_active: bool = True,
    ) -> int:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO dbo.SUBJECTS
            (
                subject_code,
                subject_name,
                is_active
            )
            OUTPUT INSERTED.subject_id
            VALUES (?, ?, ?)
            """,
            subject_code,
            subject_name,
            int(is_active),
        )

        return cursor.fetchone()[0]

    def get_subject_by_code(
        self,
        connection: pyodbc.Connection,
        subject_code: str,
    ):
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                subject_id,
                subject_code,
                subject_name,
                is_active
            FROM dbo.SUBJECTS
            WHERE subject_code = ?
            """,
            subject_code,
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return (
            row.subject_id,
            row.subject_code,
            row.subject_name,
            bool(row.is_active),
        )

    def list_active_subjects(
        self,
        connection: pyodbc.Connection,
    ) -> list[tuple]:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                subject_id,
                subject_code,
                subject_name
            FROM dbo.SUBJECTS
            WHERE is_active = 1
            ORDER BY subject_name
            """
        )

        return [
            (
                row.subject_id,
                row.subject_code,
                row.subject_name,
            )
            for row in cursor.fetchall()
        ]

    # =====================================================
    # ASSESSMENTS
    # =====================================================

    def create_assessment(
        self,
        connection: pyodbc.Connection,
        subject_id: int,
        school_year_id: int,
        assessment_name: str,
        semester: int | None,
        assessment_type: str | None,
        assessment_date: date | None,
    ) -> Assessment:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO dbo.ASSESSMENTS
            (
                subject_id,
                school_year_id,
                assessment_name,
                semester,
                assessment_type,
                assessment_date,
                status
            )
            OUTPUT
                INSERTED.assessment_id,
                INSERTED.subject_id,
                INSERTED.school_year_id,
                INSERTED.assessment_name,
                INSERTED.semester,
                INSERTED.assessment_type,
                INSERTED.assessment_date,
                INSERTED.status,
                INSERTED.created_at
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            subject_id,
            school_year_id,
            assessment_name,
            semester,
            assessment_type,
            assessment_date,
            AssessmentStatus.ACTIVE.value,
        )

        row = cursor.fetchone()

        return self._map_assessment(row)

    def get_assessment_by_id(
        self,
        connection: pyodbc.Connection,
        assessment_id: int,
    ) -> Assessment | None:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                assessment_id,
                subject_id,
                school_year_id,
                assessment_name,
                semester,
                assessment_type,
                assessment_date,
                status,
                created_at
            FROM dbo.ASSESSMENTS
            WHERE assessment_id = ?
            """,
            assessment_id,
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return self._map_assessment(row)

    def list_assessments(
        self,
        connection: pyodbc.Connection,
        school_year_id: int,
        subject_id: int | None = None,
        semester: int | None = None,
        status: AssessmentStatus | None = None,
    ) -> list[Assessment]:
        conditions = ["school_year_id = ?"]
        parameters: list[object] = [school_year_id]

        if subject_id is not None:
            conditions.append("subject_id = ?")
            parameters.append(subject_id)

        if semester is not None:
            conditions.append("semester = ?")
            parameters.append(semester)

        if status is not None:
            conditions.append("status = ?")
            parameters.append(status.value)

        sql = f"""
            SELECT
                assessment_id,
                subject_id,
                school_year_id,
                assessment_name,
                semester,
                assessment_type,
                assessment_date,
                status,
                created_at
            FROM dbo.ASSESSMENTS
            WHERE {' AND '.join(conditions)}
            ORDER BY
                assessment_date,
                assessment_id
        """

        cursor = connection.cursor()
        cursor.execute(sql, *parameters)

        return [
            self._map_assessment(row)
            for row in cursor.fetchall()
        ]

    @staticmethod
    def _map_assessment(row) -> Assessment:
        return Assessment(
            assessment_id=row.assessment_id,
            subject_id=row.subject_id,
            school_year_id=row.school_year_id,
            assessment_name=row.assessment_name,
            semester=row.semester,
            assessment_type=row.assessment_type,
            assessment_date=row.assessment_date,
            status=AssessmentStatus(row.status),
            created_at=row.created_at,
        )
