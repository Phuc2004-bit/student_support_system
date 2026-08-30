from decimal import Decimal

import pyodbc

from models.dto import Score


class ScoreRepository:
    def create(
        self,
        connection: pyodbc.Connection,
        enrollment_id: int,
        assessment_id: int,
        score_value: Decimal,
    ) -> Score:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO dbo.SCORES
            (
                enrollment_id,
                assessment_id,
                score
            )
            OUTPUT
                INSERTED.score_id,
                INSERTED.enrollment_id,
                INSERTED.assessment_id,
                INSERTED.score,
                INSERTED.created_at,
                INSERTED.updated_at
            VALUES (?, ?, ?)
            """,
            enrollment_id,
            assessment_id,
            score_value,
        )

        row = cursor.fetchone()

        return self._map_score(row)

    def get_by_id(
        self,
        connection: pyodbc.Connection,
        score_id: int,
    ) -> Score | None:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                score_id,
                enrollment_id,
                assessment_id,
                score,
                created_at,
                updated_at
            FROM dbo.SCORES
            WHERE score_id = ?
            """,
            score_id,
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return self._map_score(row)

    def get_by_enrollment_assessment(
        self,
        connection: pyodbc.Connection,
        enrollment_id: int,
        assessment_id: int,
    ) -> Score | None:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                score_id,
                enrollment_id,
                assessment_id,
                score,
                created_at,
                updated_at
            FROM dbo.SCORES
            WHERE enrollment_id = ?
              AND assessment_id = ?
            """,
            enrollment_id,
            assessment_id,
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return self._map_score(row)

    def update(
        self,
        connection: pyodbc.Connection,
        score_id: int,
        score_value: Decimal,
    ) -> Score | None:
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE dbo.SCORES
            SET
                score = ?,
                updated_at = GETDATE()
            OUTPUT
                INSERTED.score_id,
                INSERTED.enrollment_id,
                INSERTED.assessment_id,
                INSERTED.score,
                INSERTED.created_at,
                INSERTED.updated_at
            WHERE score_id = ?
            """,
            score_value,
            score_id,
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return self._map_score(row)

    def list_by_enrollment(
        self,
        connection: pyodbc.Connection,
        enrollment_id: int,
    ) -> list[Score]:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                score_id,
                enrollment_id,
                assessment_id,
                score,
                created_at,
                updated_at
            FROM dbo.SCORES
            WHERE enrollment_id = ?
            ORDER BY created_at, score_id
            """,
            enrollment_id,
        )

        return [
            self._map_score(row)
            for row in cursor.fetchall()
        ]

    @staticmethod
    def _map_score(row) -> Score:
        return Score(
            score_id=row.score_id,
            enrollment_id=row.enrollment_id,
            assessment_id=row.assessment_id,
            score=Decimal(str(row.score)),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )