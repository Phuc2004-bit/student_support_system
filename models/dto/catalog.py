from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class SchoolYear:
    school_year_id: int
    year_name: str
    start_date: date | None
    end_date: date | None
    is_current: bool


@dataclass(frozen=True, slots=True)
class Grade:
    grade_id: int
    grade_number: int
    grade_name: str | None


@dataclass(frozen=True, slots=True)
class SchoolClass:
    class_id: int
    class_name: str
    grade_id: int
    grade_number: int
    school_year_id: int
    school_year_name: str
    homeroom_teacher: str | None
    status: str

    @property
    def is_active(self) -> bool:
        return self.status == "ACTIVE"
