from dataclasses import dataclass
from models.enums import StudentStatus

@dataclass(frozen=True, slots=True)
class StudentFilter:
    search_text: str = ""
    school_year_id: int | None = None
    grade_id: int | None = None
    class_id: int | None = None
    status: StudentStatus | None = None
