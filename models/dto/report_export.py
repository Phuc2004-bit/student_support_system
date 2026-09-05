from __future__ import annotations

from dataclasses import dataclass

from models.dto.report_dto import SupportReportData
from models.enums import InterventionStatus


@dataclass(frozen=True, slots=True)
class SupportReportExportContext:
    school_year_id: int
    school_year_name: str
    grade_id: int | None = None
    grade_name: str | None = None
    class_id: int | None = None
    class_name: str | None = None
    subject_id: int | None = None
    subject_name: str | None = None
    status: str | InterventionStatus | None = None


@dataclass(frozen=True, slots=True)
class SupportReportExportData:
    context: SupportReportExportContext
    report: SupportReportData
