from dataclasses import dataclass
from datetime import date, datetime

from models.enums import EnrollmentStatus


@dataclass(frozen=True, slots=True)
class Enrollment:
    enrollment_id: int
    student_id: str
    class_id: int
    enrollment_date: date
    status: EnrollmentStatus
    created_at: datetime


@dataclass(frozen=True, slots=True)
class EnrollmentListItem:
    enrollment_id: int
    student_id: str
    student_code: str
    full_name: str
    class_id: int
    class_name: str
    grade_number: int
    school_year_id: int
    school_year_name: str
    status: EnrollmentStatus