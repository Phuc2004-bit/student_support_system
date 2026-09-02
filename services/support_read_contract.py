from __future__ import annotations

from typing import Protocol

from models.dto.report_dto import SupportReportRow
from models.enums import InterventionStatus


class SupportReadServiceContract(Protocol):
    def get_support_cases(
        self,
        school_year_id: int,
        grade_id: int | None = None,
        class_id: int | None = None,
        subject_id: int | None = None,
        status: str | InterventionStatus | None = None,
    ) -> list[SupportReportRow]:
        ...
