from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


@dataclass(frozen=True, slots=True)
class ScoreImportContext:
    school_year_id: int
    school_year_name: str
    class_id: int
    class_name: str
    subject_id: int
    subject_name: str
    assessment_id: int
    assessment_name: str


@dataclass(frozen=True, slots=True)
class ScoreImportTemplateStudent:
    student_id: str
    full_name: str


@dataclass(frozen=True, slots=True)
class ScoreImportSourceMetadata:
    school_year_name: str | None = None
    class_name: str | None = None
    subject_name: str | None = None
    assessment_name: str | None = None


@dataclass(frozen=True, slots=True)
class ScoreImportIssue:
    code: str
    field: str
    message: str


@dataclass(frozen=True, slots=True)
class ScoreImportRow:
    row_number: int
    student_id: str
    student_name: str | None
    raw_score: Any = None
    normalized_score: Decimal | None = None
    issues: tuple[ScoreImportIssue, ...] = field(default_factory=tuple)

    @property
    def is_structurally_valid(self) -> bool:
        return not self.issues


@dataclass(frozen=True, slots=True)
class ScoreImportWorkbook:
    file_name: str
    sheet_name: str
    metadata: ScoreImportSourceMetadata
    rows: tuple[ScoreImportRow, ...]

