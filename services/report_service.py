from __future__ import annotations

from models.dto.report_dto import (
    SupportReportData,
    SupportReportRow,
    SupportReportSummary,
)
from models.enums import InterventionStatus
from exceptions import ValidationError
from repositories.report_repository import ReportRepository


class ReportService:
    def __init__(
        self,
        db,
        report_repository: ReportRepository | None = None,
    ):
        self.db = db
        self.report_repository = (
            report_repository or ReportRepository()
        )

    def get_support_cases(
        self,
        school_year_id: int,
        grade_id: int | None = None,
        class_id: int | None = None,
        subject_id: int | None = None,
        status: str | InterventionStatus | None = None,
    ) -> list[SupportReportRow]:
        normalized_status = self._validate_filters(
            school_year_id=school_year_id,
            grade_id=grade_id,
            class_id=class_id,
            subject_id=subject_id,
            status=status,
        )

        with self.db.transaction() as connection:
            return self.report_repository.list_support_cases(
                connection=connection,
                school_year_id=school_year_id,
                grade_id=grade_id,
                class_id=class_id,
                subject_id=subject_id,
                status=normalized_status,
            )

    def get_support_summary(
        self,
        school_year_id: int,
        grade_id: int | None = None,
        class_id: int | None = None,
        subject_id: int | None = None,
    ) -> SupportReportSummary:
        self._validate_filters(
            school_year_id=school_year_id,
            grade_id=grade_id,
            class_id=class_id,
            subject_id=subject_id,
            status=None,
        )

        with self.db.transaction() as connection:
            return self.report_repository.get_support_summary(
                connection=connection,
                school_year_id=school_year_id,
                grade_id=grade_id,
                class_id=class_id,
                subject_id=subject_id,
            )

    def get_support_report(
        self,
        school_year_id: int,
        grade_id: int | None = None,
        class_id: int | None = None,
        subject_id: int | None = None,
        status: str | InterventionStatus | None = None,
    ) -> SupportReportData:
        normalized_status = self._validate_filters(
            school_year_id=school_year_id,
            grade_id=grade_id,
            class_id=class_id,
            subject_id=subject_id,
            status=status,
        )

        # Summary và rows dùng cùng một transaction để UI nhận được
        # một gói dữ liệu báo cáo nhất quán theo cùng bộ lọc.
        with self.db.transaction() as connection:
            summary = self.report_repository.get_support_summary(
                connection=connection,
                school_year_id=school_year_id,
                grade_id=grade_id,
                class_id=class_id,
                subject_id=subject_id,
            )

            rows = self.report_repository.list_support_cases(
                connection=connection,
                school_year_id=school_year_id,
                grade_id=grade_id,
                class_id=class_id,
                subject_id=subject_id,
                status=normalized_status,
            )

        if normalized_status is not None:
            summary = self._summary_from_rows(rows)

        return SupportReportData(
            summary=summary,
            rows=tuple(rows),
        )

    @staticmethod
    def _summary_from_rows(
        rows: list[SupportReportRow],
    ) -> SupportReportSummary:
        counts = {
            status.value: 0
            for status in InterventionStatus
        }
        for row in rows:
            counts[row.status] += 1
        return SupportReportSummary(
            total_cases=len(rows),
            detected_count=counts[InterventionStatus.DETECTED.value],
            planned_count=counts[InterventionStatus.PLANNED.value],
            in_progress_count=counts[InterventionStatus.IN_PROGRESS.value],
            waiting_review_count=counts[
                InterventionStatus.WAITING_REVIEW.value
            ],
            continue_count=counts[InterventionStatus.CONTINUE.value],
            completed_count=counts[InterventionStatus.COMPLETED.value],
        )

    @classmethod
    def _validate_filters(
        cls,
        school_year_id: int,
        grade_id: int | None,
        class_id: int | None,
        subject_id: int | None,
        status: str | InterventionStatus | None,
    ) -> str | None:
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

        if status is None:
            return None

        if isinstance(status, InterventionStatus):
            return status.value

        if not isinstance(status, str):
            raise ValidationError(
                "Trạng thái hồ sơ bổ trợ không hợp lệ."
            )

        normalized = status.strip().upper()
        valid_statuses = {
            item.value
            for item in InterventionStatus
        }

        if normalized not in valid_statuses:
            raise ValidationError(
                "Trạng thái hồ sơ bổ trợ không hợp lệ."
            )

        return normalized

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

        # bool là subclass của int trong Python, nên phải chặn riêng.
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value <= 0
        ):
            raise ValidationError(
                f"{field_name} phải là số nguyên dương."
            )
