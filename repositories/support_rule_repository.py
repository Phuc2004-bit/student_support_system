from decimal import Decimal

import pyodbc

from models.dto import SupportRule


class SupportRuleRepository:
    def create(
        self,
        connection: pyodbc.Connection,
        subject_id: int,
        school_year_id: int,
        threshold: Decimal,
        is_active: bool = True,
    ) -> SupportRule:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO dbo.SUPPORT_RULES
            (
                subject_id,
                school_year_id,
                threshold,
                is_active
            )
            OUTPUT
                INSERTED.rule_id,
                INSERTED.subject_id,
                INSERTED.school_year_id,
                INSERTED.threshold,
                INSERTED.is_active,
                INSERTED.created_at,
                INSERTED.updated_at
            VALUES (?, ?, ?, ?)
            """,
            subject_id,
            school_year_id,
            threshold,
            int(is_active),
        )

        row = cursor.fetchone()

        return self._map_rule(row)

    def get_active_rule(
        self,
        connection: pyodbc.Connection,
        subject_id: int,
        school_year_id: int,
    ) -> SupportRule | None:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT TOP 1
                rule_id,
                subject_id,
                school_year_id,
                threshold,
                is_active,
                created_at,
                updated_at
            FROM dbo.SUPPORT_RULES
            WHERE subject_id = ?
              AND school_year_id = ?
              AND is_active = 1
            ORDER BY rule_id DESC
            """,
            subject_id,
            school_year_id,
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return self._map_rule(row)

    def update_threshold(
        self,
        connection: pyodbc.Connection,
        rule_id: int,
        threshold: Decimal,
    ) -> SupportRule | None:
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE dbo.SUPPORT_RULES
            SET
                threshold = ?,
                updated_at = GETDATE()
            OUTPUT
                INSERTED.rule_id,
                INSERTED.subject_id,
                INSERTED.school_year_id,
                INSERTED.threshold,
                INSERTED.is_active,
                INSERTED.created_at,
                INSERTED.updated_at
            WHERE rule_id = ?
            """,
            threshold,
            rule_id,
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return self._map_rule(row)

    def set_active(
        self,
        connection: pyodbc.Connection,
        rule_id: int,
        is_active: bool,
    ) -> SupportRule | None:
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE dbo.SUPPORT_RULES
            SET
                is_active = ?,
                updated_at = GETDATE()
            OUTPUT
                INSERTED.rule_id,
                INSERTED.subject_id,
                INSERTED.school_year_id,
                INSERTED.threshold,
                INSERTED.is_active,
                INSERTED.created_at,
                INSERTED.updated_at
            WHERE rule_id = ?
            """,
            int(is_active),
            rule_id,
        )

        row = cursor.fetchone()

        if row is None:
            return None

        return self._map_rule(row)

    @staticmethod
    def _map_rule(row) -> SupportRule:
        return SupportRule(
            rule_id=row.rule_id,
            subject_id=row.subject_id,
            school_year_id=row.school_year_id,
            threshold=Decimal(str(row.threshold)),
            is_active=bool(row.is_active),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )