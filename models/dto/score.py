from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class ScoreCreateData:
    enrollment_id: int
    assessment_id: int
    score_value: Decimal


@dataclass(frozen=True, slots=True)
class ScoreRosterItem:
    enrollment_id: int
    student_id: str
    student_code: str
    full_name: str
    assessment_id: int
    score_id: int | None
    score: Decimal | None


@dataclass(frozen=True, slots=True)
class Score:
    score_id: int
    enrollment_id: int
    assessment_id: int
    score: Decimal
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class ScoreListItem:
    score_id: int
    enrollment_id: int
    student_id: str
    student_code: str
    full_name: str
    class_name: str
    subject_name: str
    assessment_name: str
    score: Decimal
