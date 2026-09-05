from __future__ import annotations

from typing import Protocol

from models.dto import InterventionDetail
from models.dto.report_dto import SupportReportData, SupportReportRow
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

    def get_support_report(
        self,
        school_year_id: int,
        grade_id: int | None = None,
        class_id: int | None = None,
        subject_id: int | None = None,
        status: str | InterventionStatus | None = None,
    ) -> SupportReportData:
        ...


class InterventionDetailServiceContract(Protocol):
    def get_intervention_detail(
        self,
        intervention_id: int,
    ) -> InterventionDetail:
        ...
