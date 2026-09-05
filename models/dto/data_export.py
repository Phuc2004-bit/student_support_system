from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from models.dto.student_filter import StudentFilter


@dataclass(frozen=True, slots=True)
class StudentExportContext:
    filters: StudentFilter
    school_year_name: str | None = None
    grade_name: str | None = None
    class_name: str | None = None


@dataclass(frozen=True, slots=True)
class StudentExportRow:
    student_id: str
    student_code: str
    full_name: str
    date_of_birth: date | None
    gender: str | None
    school_year_name: str | None
    grade_number: int | None
    class_name: str | None


@dataclass(frozen=True, slots=True)
class StudentExportData:
    context: StudentExportContext
    rows: tuple[StudentExportRow, ...]


@dataclass(frozen=True, slots=True)
class ScoreExportContext:
    school_year_id: int
    school_year_name: str
    class_id: int
    class_name: str
    subject_id: int
    subject_name: str
    assessment_id: int
    assessment_name: str


@dataclass(frozen=True, slots=True)
class ScoreExportRow:
    enrollment_id: int
    student_id: str
    student_code: str
    full_name: str
    score: Decimal | None


@dataclass(frozen=True, slots=True)
class ScoreExportData:
    context: ScoreExportContext
    rows: tuple[ScoreExportRow, ...]
