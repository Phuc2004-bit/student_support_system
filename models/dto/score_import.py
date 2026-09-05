from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
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


class ScoreImportIssueSeverity(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"


@dataclass(frozen=True, slots=True)
class ScoreImportIssue:
    code: str
    field: str
    message: str
    severity: ScoreImportIssueSeverity = ScoreImportIssueSeverity.ERROR

    @property
    def is_blocking(self) -> bool:
        return self.severity == ScoreImportIssueSeverity.ERROR


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


@dataclass(frozen=True, slots=True)
class ScoreImportPreviewRow:
    row_number: int
    student_id: str
    student_name_excel: str | None
    student_name_db: str | None
    enrollment_id: int | None
    normalized_score: Decimal | None
    issues: tuple[ScoreImportIssue, ...] = field(default_factory=tuple)

    @property
    def is_valid(self) -> bool:
        return not any(issue.is_blocking for issue in self.issues)


@dataclass(frozen=True, slots=True)
class ScoreImportPreview:
    context: ScoreImportContext
    rows: tuple[ScoreImportPreviewRow, ...]

    @property
    def valid_count(self) -> int:
        return sum(row.is_valid for row in self.rows)

    @property
    def invalid_count(self) -> int:
        return len(self.rows) - self.valid_count

    @property
    def can_commit(self) -> bool:
        return bool(self.rows) and self.invalid_count == 0


@dataclass(frozen=True, slots=True)
class ScoreImportTransactionResult:
    assessment_id: int
    imported_count: int
    intervention_created_count: int
    score_ids: tuple[int, ...]
    intervention_ids: tuple[int, ...]

    @property
    def success(self) -> bool:
        return True
