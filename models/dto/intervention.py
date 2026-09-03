from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

from models.enums import (
    InterventionStatus,
    ReviewResult,
)


@dataclass(frozen=True, slots=True)
class Intervention:
    intervention_id: int
    enrollment_id: int
    subject_id: int
    trigger_score_id: int
    responsible_user_id: int | None
    detected_date: date
    start_date: date | None
    status: InterventionStatus
    support_method: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class InterventionReviewItem:
    review_id: int
    intervention_id: int
    score_id: int
    review_date: date
    result: ReviewResult
    notes: str | None
    created_at: datetime
    score: Decimal | None = field(default=None, compare=False)


@dataclass(frozen=True, slots=True)
class InterventionDetail:
    intervention_id: int
    enrollment_id: int
    student_id: str
    student_code: str
    full_name: str
    class_name: str
    subject_id: int
    subject_name: str
    trigger_score_id: int
    trigger_score: Decimal
    responsible_user_id: int | None
    responsible_user_name: str | None
    detected_date: date
    start_date: date | None
    status: InterventionStatus
    support_method: str | None
    notes: str | None
    created_at: datetime
    updated_at: datetime
    reviews: tuple[InterventionReviewItem, ...]
    grade_number: int | None = None
    school_year_id: int | None = None
    school_year_name: str | None = None
    subject_code: str | None = None
    trigger_assessment_name: str | None = None


@dataclass(frozen=True, slots=True)
class InterventionHistoryItem:
    intervention_id: int
    enrollment_id: int
    student_id: str
    class_name: str
    subject_name: str
    trigger_score: Decimal
    detected_date: date
    status: InterventionStatus
    support_method: str | None
