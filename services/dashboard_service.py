from __future__ import annotations

from exceptions import ValidationError
from models.dto.dashboard_dto import DashboardData
from repositories.dashboard_repository import DashboardRepository


class DashboardService:
    def __init__(
        self,
        db,
        dashboard_repository: DashboardRepository | None = None,
    ) -> None:
        self.db = db
        self.dashboard_repository = (
            dashboard_repository
            or DashboardRepository()
        )

    def get_dashboard(
        self,
        school_year_id: int,
        grade_id: int | None = None,
        class_id: int | None = None,
        subject_id: int | None = None,
    ) -> DashboardData:
        self._validate_filters(
            school_year_id=school_year_id,
            grade_id=grade_id,
            class_id=class_id,
            subject_id=subject_id,
        )

        # Cả 3 phần Dashboard dùng cùng transaction/connection
        # để UI nhận một snapshot dữ liệu nhất quán.
        with self.db.transaction() as connection:
            summary = self.dashboard_repository.get_summary(
                connection=connection,
                school_year_id=school_year_id,
                grade_id=grade_id,
                class_id=class_id,
                subject_id=subject_id,
            )

            status_breakdown = (
                self.dashboard_repository.get_status_breakdown(
                    connection=connection,
                    school_year_id=school_year_id,
                    grade_id=grade_id,
                    class_id=class_id,
                    subject_id=subject_id,
                )
            )

            attention_items = (
                self.dashboard_repository.list_attention_items(
                    connection=connection,
                    school_year_id=school_year_id,
                    grade_id=grade_id,
                    class_id=class_id,
                    subject_id=subject_id,
                )
            )

        return DashboardData(
            summary=summary,
            status_breakdown=tuple(status_breakdown),
            attention_items=tuple(attention_items),
        )

    @classmethod
    def _validate_filters(
        cls,
        school_year_id: int,
        grade_id: int | None,
        class_id: int | None,
        subject_id: int | None,
    ) -> None:
        cls._validate_positive_id(
            "school_year_id",
            school_year_id,
            required=True,
        )
        cls._validate_positive_id(
            "grade_id",
            grade_id,
        )
        cls._validate_positive_id(
            "class_id",
            class_id,
        )
        cls._validate_positive_id(
            "subject_id",
            subject_id,
        )

    @staticmethod
    def _validate_positive_id(
        field_name: str,
        value: int | None,
        required: bool = False,
    ) -> None:
        if value is None:
            if required:
                raise ValidationError(
                    f"{field_name} là bắt buộc."
                )
            return

        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value <= 0
        ):
            raise ValidationError(
                f"{field_name} phải là số nguyên dương."
            )
