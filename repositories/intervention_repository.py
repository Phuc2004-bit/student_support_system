from datetime import date

import pyodbc

from models.dto import (
    Intervention,
    InterventionHistoryItem,
    InterventionReviewItem,
)
from models.enums import (
    InterventionStatus,
    ReviewResult,
)


class InterventionRepository:
    OPEN_STATUSES = (
        InterventionStatus.DETECTED.value,
        InterventionStatus.PLANNED.value,
        InterventionStatus.IN_PROGRESS.value,
        InterventionStatus.WAITING_REVIEW.value,
        InterventionStatus.CONTINUE.value,
    )

    def create(
        self,
        connection: pyodbc.Connection,
        enrollment_id: int,
        subject_id: int,
        trigger_score_id: int,
        detected_date: date,
        responsible_user_id: int | None = None,
    ) -> Intervention:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO dbo.INTERVENTIONS
            (
                enrollment_id,
                subject_id,
                trigger_score_id,
                responsible_user_id,
                detected_date,
                start_date,
                status,
                support_method,
                notes
            )
            OUTPUT
                INSERTED.intervention_id,
                INSERTED.enrollment_id,
                INSERTED.subject_id,
                INSERTED.trigger_score_id,
                INSERTED.responsible_user_id,
                INSERTED.detected_date,
                INSERTED.start_date,
                INSERTED.status,
                INSERTED.support_method,
                INSERTED.notes,
                INSERTED.created_at,
                INSERTED.updated_at
            VALUES (?, ?, ?, ?, ?, NULL, ?, NULL, NULL)
            """,
            enrollment_id,
            subject_id,
            trigger_score_id,
            responsible_user_id,
            detected_date,
            InterventionStatus.DETECTED.value,
        )

        return self._map_intervention(cursor.fetchone())

    def get_by_id(
        self,
        connection: pyodbc.Connection,
        intervention_id: int,
    ) -> Intervention | None:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                intervention_id,
                enrollment_id,
                subject_id,
                trigger_score_id,
                responsible_user_id,
                detected_date,
                start_date,
                status,
                support_method,
                notes,
                created_at,
                updated_at
            FROM dbo.INTERVENTIONS
            WHERE intervention_id = ?
            """,
            intervention_id,
        )

        row = cursor.fetchone()

        return (
            self._map_intervention(row)
            if row is not None
            else None
        )

    def get_open(
        self,
        connection: pyodbc.Connection,
        enrollment_id: int,
        subject_id: int,
    ) -> Intervention | None:
        cursor = connection.cursor()

        placeholders = ", ".join(
            "?" for _ in self.OPEN_STATUSES
        )

        sql = f"""
            SELECT TOP 1
                intervention_id,
                enrollment_id,
                subject_id,
                trigger_score_id,
                responsible_user_id,
                detected_date,
                start_date,
                status,
                support_method,
                notes,
                created_at,
                updated_at
            FROM dbo.INTERVENTIONS
            WHERE enrollment_id = ?
              AND subject_id = ?
              AND status IN ({placeholders})
            ORDER BY intervention_id DESC
        """

        cursor.execute(
            sql,
            enrollment_id,
            subject_id,
            *self.OPEN_STATUSES,
        )

        row = cursor.fetchone()

        return (
            self._map_intervention(row)
            if row is not None
            else None
        )

    def update_status(
        self,
        connection: pyodbc.Connection,
        intervention_id: int,
        status: InterventionStatus,
    ) -> Intervention | None:
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE dbo.INTERVENTIONS
            SET
                status = ?,
                updated_at = GETDATE()
            OUTPUT
                INSERTED.intervention_id,
                INSERTED.enrollment_id,
                INSERTED.subject_id,
                INSERTED.trigger_score_id,
                INSERTED.responsible_user_id,
                INSERTED.detected_date,
                INSERTED.start_date,
                INSERTED.status,
                INSERTED.support_method,
                INSERTED.notes,
                INSERTED.created_at,
                INSERTED.updated_at
            WHERE intervention_id = ?
            """,
            status.value,
            intervention_id,
        )

        row = cursor.fetchone()

        return (
            self._map_intervention(row)
            if row is not None
            else None
        )

    def update_plan(
        self,
        connection: pyodbc.Connection,
        intervention_id: int,
        responsible_user_id: int,
        start_date: date,
        support_method: str | None,
        notes: str | None,
    ) -> Intervention | None:
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE dbo.INTERVENTIONS
            SET
                responsible_user_id = ?,
                start_date = ?,
                support_method = ?,
                notes = ?,
                updated_at = GETDATE()
            OUTPUT
                INSERTED.intervention_id,
                INSERTED.enrollment_id,
                INSERTED.subject_id,
                INSERTED.trigger_score_id,
                INSERTED.responsible_user_id,
                INSERTED.detected_date,
                INSERTED.start_date,
                INSERTED.status,
                INSERTED.support_method,
                INSERTED.notes,
                INSERTED.created_at,
                INSERTED.updated_at
            WHERE intervention_id = ?
            """,
            responsible_user_id,
            start_date,
            support_method,
            notes,
            intervention_id,
        )

        row = cursor.fetchone()

        return (
            self._map_intervention(row)
            if row is not None
            else None
        )

    def create_review(
        self,
        connection: pyodbc.Connection,
        intervention_id: int,
        score_id: int,
        review_date: date,
        result: ReviewResult,
        notes: str | None = None,
    ) -> InterventionReviewItem:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO dbo.INTERVENTION_REVIEWS
            (
                intervention_id,
                score_id,
                review_date,
                result,
                notes
            )
            OUTPUT
                INSERTED.review_id,
                INSERTED.intervention_id,
                INSERTED.score_id,
                INSERTED.review_date,
                INSERTED.result,
                INSERTED.notes,
                INSERTED.created_at
            VALUES (?, ?, ?, ?, ?)
            """,
            intervention_id,
            score_id,
            review_date,
            result.value,
            notes,
        )

        return self._map_review(cursor.fetchone())

    def list_reviews(
        self,
        connection: pyodbc.Connection,
        intervention_id: int,
    ) -> list[InterventionReviewItem]:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                review_id,
                intervention_id,
                score_id,
                review_date,
                result,
                notes,
                created_at
            FROM dbo.INTERVENTION_REVIEWS
            WHERE intervention_id = ?
            ORDER BY review_date, review_id
            """,
            intervention_id,
        )

        return [
            self._map_review(row)
            for row in cursor.fetchall()
        ]

    def list_by_student(
        self,
        connection: pyodbc.Connection,
        student_id: str,
    ) -> list[InterventionHistoryItem]:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT
                i.intervention_id, i.enrollment_id, e.student_id,
                c.class_name, su.subject_name,
                trigger_score.score AS trigger_score,
                i.detected_date, i.status, i.support_method
            FROM dbo.INTERVENTIONS i
            INNER JOIN dbo.STUDENT_ENROLLMENTS e
                ON e.enrollment_id = i.enrollment_id
            INNER JOIN dbo.CLASSES c
                ON c.class_id = e.class_id
            INNER JOIN dbo.SUBJECTS su
                ON su.subject_id = i.subject_id
            INNER JOIN dbo.SCORES trigger_score
                ON trigger_score.score_id = i.trigger_score_id
            WHERE e.student_id = ?
            ORDER BY i.detected_date, i.intervention_id
            """,
            student_id,
        )
        return [
            self._map_history_item(row)
            for row in cursor.fetchall()
        ]

    @staticmethod
    def _map_intervention(row) -> Intervention:
        return Intervention(
            intervention_id=row.intervention_id,
            enrollment_id=row.enrollment_id,
            subject_id=row.subject_id,
            trigger_score_id=row.trigger_score_id,
            responsible_user_id=row.responsible_user_id,
            detected_date=row.detected_date,
            start_date=row.start_date,
            status=InterventionStatus(row.status),
            support_method=row.support_method,
            notes=row.notes,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _map_review(row) -> InterventionReviewItem:
        return InterventionReviewItem(
            review_id=row.review_id,
            intervention_id=row.intervention_id,
            score_id=row.score_id,
            review_date=row.review_date,
            result=ReviewResult(row.result),
            notes=row.notes,
            created_at=row.created_at,
        )

    @staticmethod
    def _map_history_item(row) -> InterventionHistoryItem:
        return InterventionHistoryItem(
            intervention_id=row.intervention_id,
            enrollment_id=row.enrollment_id,
            student_id=row.student_id,
            class_name=row.class_name,
            subject_name=row.subject_name,
            trigger_score=Decimal(str(row.trigger_score)),
            detected_date=row.detected_date,
            status=InterventionStatus(row.status),
            support_method=row.support_method,
        )
