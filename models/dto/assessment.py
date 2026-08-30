from dataclasses import dataclass
from datetime import date, datetime

from models.enums import AssessmentStatus


@dataclass(frozen=True, slots=True)
class Assessment:
    assessment_id: int
    subject_id: int
    school_year_id: int
    assessment_name: str
    semester: int | None
    assessment_type: str | None
    assessment_date: date | None
    status: AssessmentStatus
    created_at: datetime