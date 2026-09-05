from __future__ import annotations
import pyodbc
from models.dto.student_filter import StudentFilter
from models.dto.student_list import StudentListItem
from models.enums import EnrollmentStatus, StudentStatus

class StudentListRepository:
    def list_students(
        self,
        connection: pyodbc.Connection,
        filters: StudentFilter | None = None,
    ) -> list[StudentListItem]:
        filters = filters or StudentFilter()
        where = []
        params: list[object] = [EnrollmentStatus.ACTIVE.value]

        text = filters.search_text.strip()
        if text:
            where.append("(s.student_code LIKE ? OR s.full_name LIKE ?)")
            pattern = f"%{text}%"
            params.extend([pattern, pattern])
        if filters.status is not None:
            where.append("s.status = ?")
            params.append(filters.status.value)
        if filters.school_year_id is not None:
            where.append("current_class.school_year_id = ?")
            params.append(filters.school_year_id)
        if filters.grade_id is not None:
            where.append("current_class.grade_id = ?")
            params.append(filters.grade_id)
        if filters.class_id is not None:
            where.append("current_class.class_id = ?")
            params.append(filters.class_id)

        where_sql = ("WHERE " + " AND ".join(where)) if where else ""

        sql = f"""
            SELECT
                s.student_id, s.student_code, s.full_name,
                s.date_of_birth, s.gender,
                current_class.class_name,
                current_class.grade_number,
                s.status,
                current_class.school_year_name
            FROM dbo.STUDENTS s
            OUTER APPLY
            (
                SELECT TOP (1)
                    c.class_id,
                    c.class_name,
                    c.grade_id,
                    g.grade_number,
                    sy.school_year_id,
                    sy.year_name AS school_year_name
                FROM dbo.STUDENT_ENROLLMENTS e
                INNER JOIN dbo.CLASSES c ON c.class_id = e.class_id
                INNER JOIN dbo.GRADES g ON g.grade_id = c.grade_id
                INNER JOIN dbo.SCHOOL_YEARS sy
                    ON sy.school_year_id = c.school_year_id
                WHERE e.student_id = s.student_id
                  AND e.status = ?
                ORDER BY sy.start_date DESC, e.enrollment_id DESC
            ) current_class
            {where_sql}
            ORDER BY s.full_name, s.student_code
        """
        cursor = connection.cursor()
        cursor.execute(sql, *params)
        return [self._map_list_item(row) for row in cursor.fetchall()]

    def list_students_with_current_class(self, connection):
        return self.list_students(connection, StudentFilter())

    @staticmethod
    def _map_list_item(row) -> StudentListItem:
        return StudentListItem(
            student_id=row.student_id,
            student_code=row.student_code,
            full_name=row.full_name,
            date_of_birth=row.date_of_birth,
            gender=row.gender,
            current_class_name=row.class_name,
            current_grade_number=row.grade_number,
            status=StudentStatus(row.status),
            current_school_year_name=row.school_year_name,
        )
