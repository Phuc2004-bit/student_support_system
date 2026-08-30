from dataclasses import dataclass
from datetime import date, datetime

from models.enums import StudentStatus


@dataclass(frozen=True, slots=True)
class Student:
    student_id: str
    student_code: str
    full_name: str
    date_of_birth: date | None
    gender: str | None
    phone: str | None
    email: str | None
    address: str | None
    status: StudentStatus
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class StudentCreateData:
    student_code: str
    full_name: str
    date_of_birth: date | None = None
    gender: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None


@dataclass(frozen=True, slots=True)
class StudentUpdateData:
    full_name: str
    date_of_birth: date | None = None
    gender: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None