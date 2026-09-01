from __future__ import annotations

import pyodbc

from models.dto.dashboard_dto import (
    DashboardAttentionItem,
    DashboardStatusItem,
    DashboardSummary,
)
from models.enums import InterventionStatus


class DashboardRepository:
    """
    Read-only repository cho Dashboard.

    Repository chỉ truy vấn và ánh xạ dữ liệu.
    Không commit/rollback và không chứa business workflow.
    """

    OPEN_STATUSES = (
        InterventionStatus.DETECTED.value,
        InterventionStatus.PLANNED.value,
        InterventionStatus.IN_PROGRESS.value,
        InterventionStatus.WAITING_REVIEW.value,
        InterventionStatus.CONTINUE.value,
    )

    def get_summary(
        self,
        connection: pyodbc.Connection,
        school_year_id: int,
        grade_id: int | None = None,
        class_id: int | None = None,
        subject_id: int | None = None,
    ) -> DashboardSummary:
        cursor = connection.cursor()

        where_sql, params = self._build_filter_sql(
            school_year_id=school_year_id,
            grade_id=grade_id,
            class_id=class_id,
            subject_id=subject_id,
        )

        open_placeholders = ", ".join(
            "?" for _ in self.OPEN_STATUSES
        )

        sql = f"""
            SELECT
                COUNT(DISTINCT e.student_id) AS total_students,

                COUNT(DISTINCT CASE
                    WHEN i.status IN ({open_placeholders})
                    THEN e.student_id
                END) AS needs_support_count,

                SUM(CASE
                    WHEN i.status = ? THEN 1 ELSE 0
                END) AS in_progress_count,

                SUM(CASE
                    WHEN i.status = ? THEN 1 ELSE 0
                END) AS waiting_review_count,

                SUM(CASE
                    WHEN i.status = ? THEN 1 ELSE 0
                END) AS completed_count,

                SUM(CASE
                    WHEN i.status = ? THEN 1 ELSE 0
                END) AS continue_count

            FROM dbo.STUDENT_ENROLLMENTS e
            INNER JOIN dbo.CLASSES c
                ON c.class_id = e.class_id
            INNER JOIN dbo.GRADES g
                ON g.grade_id = c.grade_id
            LEFT JOIN dbo.INTERVENTIONS i
                ON i.enrollment_id = e.enrollment_id
            {where_sql}
        """

        cursor.execute(
            sql,
            *self.OPEN_STATUSES,
            InterventionStatus.IN_PROGRESS.value,
            InterventionStatus.WAITING_REVIEW.value,
            InterventionStatus.COMPLETED.value,
            InterventionStatus.CONTINUE.value,
            *params,
        )

        row = cursor.fetchone()

        return DashboardSummary(
            total_students=int(row.total_students or 0),
            needs_support_count=int(row.needs_support_count or 0),
            in_progress_count=int(row.in_progress_count or 0),
            waiting_review_count=int(row.waiting_review_count or 0),
            completed_count=int(row.completed_count or 0),
            continue_count=int(row.continue_count or 0),
        )

    def get_status_breakdown(
        self,
        connection: pyodbc.Connection,
        school_year_id: int,
        grade_id: int | None = None,
        class_id: int | None = None,
        subject_id: int | None = None,
    ) -> list[DashboardStatusItem]:
        cursor = connection.cursor()

        where_sql, params = self._build_filter_sql(
            school_year_id=school_year_id,
            grade_id=grade_id,
            class_id=class_id,
            subject_id=subject_id,
        )

        cursor.execute(
            f"""
            SELECT
                i.status,
                COUNT_BIG(*) AS item_count
            FROM dbo.INTERVENTIONS i
            INNER JOIN dbo.STUDENT_ENROLLMENTS e
                ON e.enrollment_id = i.enrollment_id
            INNER JOIN dbo.CLASSES c
                ON c.class_id = e.class_id
            INNER JOIN dbo.GRADES g
                ON g.grade_id = c.grade_id
            {where_sql}
            GROUP BY i.status
            ORDER BY i.status
            """,
            *params,
        )

        return [
            DashboardStatusItem(
                status=row.status,
                count=int(row.item_count),
            )
            for row in cursor.fetchall()
        ]

    def list_attention_items(
        self,
        connection: pyodbc.Connection,
        school_year_id: int,
        grade_id: int | None = None,
        class_id: int | None = None,
        subject_id: int | None = None,
        limit: int = 20,
    ) -> list[DashboardAttentionItem]:
        cursor = connection.cursor()

        where_sql, params = self._build_filter_sql(
            school_year_id=school_year_id,
            grade_id=grade_id,
            class_id=class_id,
            subject_id=subject_id,
        )

        open_placeholders = ", ".join(
            "?" for _ in self.OPEN_STATUSES
        )

        cursor.execute(
            f"""
            SELECT TOP (?)
                i.intervention_id,
                s.student_code,
                s.full_name,
                g.grade_number,
                c.class_name,
                sub.subject_code,
                sub.subject_name,
                i.status,
                i.detected_date,
                trigger_score.score AS trigger_score,
                latest_review.latest_review_score
            FROM dbo.INTERVENTIONS i
            INNER JOIN dbo.STUDENT_ENROLLMENTS e
                ON e.enrollment_id = i.enrollment_id
            INNER JOIN dbo.STUDENTS s
                ON s.student_id = e.student_id
            INNER JOIN dbo.CLASSES c
                ON c.class_id = e.class_id
            INNER JOIN dbo.GRADES g
                ON g.grade_id = c.grade_id
            INNER JOIN dbo.SUBJECTS sub
                ON sub.subject_id = i.subject_id
            INNER JOIN dbo.SCORES trigger_score
                ON trigger_score.score_id = i.trigger_score_id
            OUTER APPLY
            (
                SELECT TOP 1
                    review_score.score AS latest_review_score
                FROM dbo.INTERVENTION_REVIEWS ir
                INNER JOIN dbo.SCORES review_score
                    ON review_score.score_id = ir.score_id
                WHERE ir.intervention_id = i.intervention_id
                ORDER BY ir.review_date DESC, ir.review_id DESC
            ) latest_review
            {where_sql}
              AND i.status IN ({open_placeholders})
            ORDER BY
                CASE i.status
                    WHEN 'WAITING_REVIEW' THEN 1
                    WHEN 'CONTINUE' THEN 2
                    WHEN 'DETECTED' THEN 3
                    WHEN 'PLANNED' THEN 4
                    WHEN 'IN_PROGRESS' THEN 5
                    ELSE 6
                END,
                i.detected_date,
                i.intervention_id
            """,
            limit,
            *params,
            *self.OPEN_STATUSES,
        )

        return [
            DashboardAttentionItem(
                intervention_id=row.intervention_id,
                student_code=row.student_code,
                full_name=row.full_name,
                grade_number=row.grade_number,
                class_name=row.class_name,
                subject_code=row.subject_code,
                subject_name=row.subject_name,
                status=row.status,
                detected_date=row.detected_date,
                trigger_score=row.trigger_score,
                latest_review_score=row.latest_review_score,
            )
            for row in cursor.fetchall()
        ]

    @staticmethod
    def _build_filter_sql(
        school_year_id: int,
        grade_id: int | None,
        class_id: int | None,
        subject_id: int | None,
    ) -> tuple[str, list[int]]:
        conditions = [
            "c.school_year_id = ?",
        ]
        params: list[int] = [
            school_year_id,
        ]

        if grade_id is not None:
            conditions.append(
                "c.grade_id = ?"
            )
            params.append(grade_id)

        if class_id is not None:
            conditions.append(
                "c.class_id = ?"
            )
            params.append(class_id)

        if subject_id is not None:
            conditions.append(
                "i.subject_id = ?"
            )
            params.append(subject_id)

        return (
            "WHERE " + " AND ".join(conditions),
            params,
        )
