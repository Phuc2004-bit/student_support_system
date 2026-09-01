from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class DashboardSummary:
    total_students: int
    needs_support_count: int
    in_progress_count: int
    waiting_review_count: int
    completed_count: int
    continue_count: int


@dataclass(frozen=True)
class DashboardStatusItem:
    status: str
    count: int


@dataclass(frozen=True)
class DashboardAttentionItem:
    intervention_id: int
    student_code: str
    full_name: str
    grade_number: int
    class_name: str
    subject_code: str
    subject_name: str
    status: str
    detected_date: date
    trigger_score: Decimal
    latest_review_score: Decimal | None = None


@dataclass(frozen=True)
class DashboardData:
    summary: DashboardSummary
    status_breakdown: tuple[DashboardStatusItem, ...]
    attention_items: tuple[DashboardAttentionItem, ...]
