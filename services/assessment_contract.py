from typing import Protocol

from models.dto import Assessment
from models.enums import AssessmentStatus


class AssessmentReadServiceContract(Protocol):
    def get_assessment(
        self,
        assessment_id: int,
    ) -> Assessment:
        ...

    def list_assessments(
        self,
        school_year_id: int,
        subject_id: int | None = None,
        semester: int | None = None,
        status: AssessmentStatus | None = None,
    ) -> list[Assessment]:
        ...
