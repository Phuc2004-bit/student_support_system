from dataclasses import dataclass

from models.dto.enrollment import EnrollmentListItem
from models.dto.intervention import InterventionHistoryItem
from models.dto.score import ScoreListItem
from models.dto.student import Student


@dataclass(frozen=True, slots=True)
class StudentProfileData:
    student: Student
    enrollment_history: tuple[EnrollmentListItem, ...]
    score_history: tuple[ScoreListItem, ...]
    intervention_history: tuple[InterventionHistoryItem, ...]
