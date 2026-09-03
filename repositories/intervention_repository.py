from datetime import date
from decimal import Decimal

import pyodbc

from models.dto import (
    Intervention,
    InterventionDetail,
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

    def is_score_linked_to_support(
        self,
        connection: pyodbc.Connection,
        score_id: int,
    ) -> bool:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT CASE WHEN
                EXISTS
                (
                    SELECT 1
                    FROM dbo.INTERVENTIONS
                    WHERE trigger_score_id = ?
                )
                OR EXISTS
                (
                    SELECT 1
                    FROM dbo.INTERVENTION_REVIEWS
                    WHERE score_id = ?
                )
            THEN 1 ELSE 0 END
            """,
            score_id,
            score_id,
        )
        return bool(cursor.fetchone()[0])

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

    def get_detail(
        self,
        connection: pyodbc.Connection,
        intervention_id: int,
    ) -> InterventionDetail | None:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT
                i.intervention_id,
                i.enrollment_id,
                e.student_id,
                student.student_code,
                student.full_name,
                cls.class_name,
                i.subject_id,
                subject.subject_name,
                i.trigger_score_id,
                trigger_score.score AS trigger_score,
                i.responsible_user_id,
                responsible_user.full_name AS responsible_user_name,
                i.detected_date,
                i.start_date,
                i.status,
                i.support_method,
                i.notes,
                i.created_at,
                i.updated_at,
                grade.grade_number,
                school_year.school_year_id,
                school_year.year_name AS school_year_name,
                subject.subject_code,
                trigger_assessment.assessment_name
                    AS trigger_assessment_name
            FROM dbo.INTERVENTIONS AS i
            INNER JOIN dbo.STUDENT_ENROLLMENTS AS e
                ON e.enrollment_id = i.enrollment_id
            INNER JOIN dbo.STUDENTS AS student
                ON student.student_id = e.student_id
            INNER JOIN dbo.CLASSES AS cls
                ON cls.class_id = e.class_id
            INNER JOIN dbo.GRADES AS grade
                ON grade.grade_id = cls.grade_id
            INNER JOIN dbo.SCHOOL_YEARS AS school_year
                ON school_year.school_year_id = cls.school_year_id
            INNER JOIN dbo.SUBJECTS AS subject
                ON subject.subject_id = i.subject_id
            INNER JOIN dbo.SCORES AS trigger_score
                ON trigger_score.score_id = i.trigger_score_id
            INNER JOIN dbo.ASSESSMENTS AS trigger_assessment
                ON trigger_assessment.assessment_id
                    = trigger_score.assessment_id
            LEFT JOIN dbo.USERS AS responsible_user
                ON responsible_user.user_id = i.responsible_user_id
            WHERE i.intervention_id = ?
            """,
            intervention_id,
        )
        row = cursor.fetchone()
        return self._map_detail(row) if row is not None else None

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
                review.review_id,
                review.intervention_id,
                review.score_id,
                review.review_date,
                review.result,
                review.notes,
                review.created_at,
                score.score
            FROM dbo.INTERVENTION_REVIEWS AS review
            INNER JOIN dbo.SCORES AS score
                ON score.score_id = review.score_id
            WHERE review.intervention_id = ?
            ORDER BY review.review_date, review.review_id
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
        score = getattr(row, "score", None)
        return InterventionReviewItem(
            review_id=row.review_id,
            intervention_id=row.intervention_id,
            score_id=row.score_id,
            review_date=row.review_date,
            result=ReviewResult(row.result),
            notes=row.notes,
            created_at=row.created_at,
            score=(Decimal(str(score)) if score is not None else None),
        )

    @staticmethod
    def _map_detail(row) -> InterventionDetail:
        return InterventionDetail(
            intervention_id=row.intervention_id,
            enrollment_id=row.enrollment_id,
            student_id=str(row.student_id),
            student_code=row.student_code,
            full_name=row.full_name,
            class_name=row.class_name,
            subject_id=row.subject_id,
            subject_name=row.subject_name,
            trigger_score_id=row.trigger_score_id,
            trigger_score=Decimal(str(row.trigger_score)),
            responsible_user_id=row.responsible_user_id,
            responsible_user_name=row.responsible_user_name,
            detected_date=row.detected_date,
            start_date=row.start_date,
            status=InterventionStatus(row.status),
            support_method=row.support_method,
            notes=row.notes,
            created_at=row.created_at,
            updated_at=row.updated_at,
            reviews=(),
            grade_number=row.grade_number,
            school_year_id=row.school_year_id,
            school_year_name=row.school_year_name,
            subject_code=row.subject_code,
            trigger_assessment_name=row.trigger_assessment_name,
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
