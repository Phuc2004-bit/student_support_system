from __future__ import annotations

import pyodbc

from models.dto.report_dto import (
    SupportReportRow,
    SupportReportSummary,
)


class ReportRepository:
    def list_support_cases(
        self,
        connection: pyodbc.Connection,
        school_year_id: int,
        grade_id: int | None = None,
        class_id: int | None = None,
        subject_id: int | None = None,
        status: str | None = None,
    ) -> list[SupportReportRow]:
        sql = """
            SELECT
                i.intervention_id,
                s.student_code,
                s.full_name,
                g.grade_number,
                c.class_name,
                sub.subject_code,
                sub.subject_name,
                i.detected_date,
                i.start_date,
                i.status,
                trigger_score.score AS trigger_score,
                latest_review.review_date AS latest_review_date,
                latest_review.review_score AS latest_review_score,
                latest_review.result AS latest_review_result
            FROM dbo.INTERVENTIONS AS i
            INNER JOIN dbo.STUDENT_ENROLLMENTS AS e
                ON e.enrollment_id = i.enrollment_id
            INNER JOIN dbo.STUDENTS AS s
                ON s.student_id = e.student_id
            INNER JOIN dbo.CLASSES AS c
                ON c.class_id = e.class_id
            INNER JOIN dbo.GRADES AS g
                ON g.grade_id = c.grade_id
            INNER JOIN dbo.SUBJECTS AS sub
                ON sub.subject_id = i.subject_id
            INNER JOIN dbo.SCORES AS trigger_score
                ON trigger_score.score_id = i.trigger_score_id
            OUTER APPLY
            (
                SELECT TOP (1)
                    ir.review_date,
                    review_score.score AS review_score,
                    ir.result
                FROM dbo.INTERVENTION_REVIEWS AS ir
                INNER JOIN dbo.SCORES AS review_score
                    ON review_score.score_id = ir.score_id
                WHERE ir.intervention_id = i.intervention_id
                ORDER BY
                    ir.review_date DESC,
                    ir.review_id DESC
            ) AS latest_review
            WHERE c.school_year_id = ?
        """

        params: list[object] = [school_year_id]

        if grade_id is not None:
            sql += " AND c.grade_id = ?"
            params.append(grade_id)

        if class_id is not None:
            sql += " AND c.class_id = ?"
            params.append(class_id)

        if subject_id is not None:
            sql += " AND i.subject_id = ?"
            params.append(subject_id)

        if status is not None:
            sql += " AND i.status = ?"
            params.append(status)

        sql += """
            ORDER BY
                g.grade_number,
                c.class_name,
                sub.subject_name,
                s.full_name,
                i.detected_date DESC,
                i.intervention_id DESC
        """

        cursor = connection.cursor()
        cursor.execute(sql, *params)

        return [
            self._map_support_row(row)
            for row in cursor.fetchall()
        ]

    def get_support_summary(
        self,
        connection: pyodbc.Connection,
        school_year_id: int,
        grade_id: int | None = None,
        class_id: int | None = None,
        subject_id: int | None = None,
    ) -> SupportReportSummary:
        sql = """
            SELECT
                COUNT_BIG(*) AS total_cases,
                SUM(CASE WHEN i.status = 'DETECTED' THEN 1 ELSE 0 END)
                    AS detected_count,
                SUM(CASE WHEN i.status = 'PLANNED' THEN 1 ELSE 0 END)
                    AS planned_count,
                SUM(CASE WHEN i.status = 'IN_PROGRESS' THEN 1 ELSE 0 END)
                    AS in_progress_count,
                SUM(CASE WHEN i.status = 'WAITING_REVIEW' THEN 1 ELSE 0 END)
                    AS waiting_review_count,
                SUM(CASE WHEN i.status = 'CONTINUE' THEN 1 ELSE 0 END)
                    AS continue_count,
                SUM(CASE WHEN i.status = 'COMPLETED' THEN 1 ELSE 0 END)
                    AS completed_count
            FROM dbo.INTERVENTIONS AS i
            INNER JOIN dbo.STUDENT_ENROLLMENTS AS e
                ON e.enrollment_id = i.enrollment_id
            INNER JOIN dbo.CLASSES AS c
                ON c.class_id = e.class_id
            WHERE c.school_year_id = ?
        """

        params: list[object] = [school_year_id]

        if grade_id is not None:
            sql += " AND c.grade_id = ?"
            params.append(grade_id)

        if class_id is not None:
            sql += " AND c.class_id = ?"
            params.append(class_id)

        if subject_id is not None:
            sql += " AND i.subject_id = ?"
            params.append(subject_id)

        cursor = connection.cursor()
        cursor.execute(sql, *params)
        row = cursor.fetchone()

        if row is None:
            return SupportReportSummary(
                total_cases=0,
                detected_count=0,
                planned_count=0,
                in_progress_count=0,
                waiting_review_count=0,
                continue_count=0,
                completed_count=0,
            )

        return SupportReportSummary(
            total_cases=int(row[0] or 0),
            detected_count=int(row[1] or 0),
            planned_count=int(row[2] or 0),
            in_progress_count=int(row[3] or 0),
            waiting_review_count=int(row[4] or 0),
            continue_count=int(row[5] or 0),
            completed_count=int(row[6] or 0),
        )

    @staticmethod
    def _map_support_row(row) -> SupportReportRow:
        return SupportReportRow(
            intervention_id=int(row[0]),
            student_code=row[1],
            full_name=row[2],
            grade_number=int(row[3]),
            class_name=row[4],
            subject_code=row[5],
            subject_name=row[6],
            detected_date=row[7],
            start_date=row[8],
            status=row[9],
            trigger_score=row[10],
            latest_review_date=row[11],
            latest_review_score=row[12],
            latest_review_result=row[13],
        )
