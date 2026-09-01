from dataclasses import dataclass
from datetime import date

from models.enums import StudentStatus


@dataclass(frozen=True, slots=True)
class StudentListItem:
    student_id: str
    student_code: str
    full_name: str
    date_of_birth: date | None
    gender: str | None
    current_class_name: str | None
    current_grade_number: int | None
    status: StudentStatus
