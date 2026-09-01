from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class SupportReportRow:
    intervention_id: int
    student_code: str
    full_name: str
    grade_number: int
    class_name: str
    subject_code: str
    subject_name: str
    detected_date: date
    start_date: date | None
    status: str
    trigger_score: Decimal
    latest_review_date: date | None = None
    latest_review_score: Decimal | None = None
    latest_review_result: str | None = None


@dataclass(frozen=True)
class SupportReportSummary:
    total_cases: int
    detected_count: int
    planned_count: int
    in_progress_count: int
    waiting_review_count: int
    continue_count: int
    completed_count: int


@dataclass(frozen=True)
class SupportReportData:
    summary: SupportReportSummary
    rows: tuple[SupportReportRow, ...]
