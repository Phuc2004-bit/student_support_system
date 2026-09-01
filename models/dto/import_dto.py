from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class ScoreImportRawRow:
    """Một dòng dữ liệu thô đọc trực tiếp từ Excel."""

    row_number: int
    student_code: Any
    full_name: Any = None
    class_name: Any = None
    score: Any = None


@dataclass(frozen=True)
class ScoreImportPreviewRow:
    """Một dòng sau normalize + validate + resolve dữ liệu nền."""

    row_number: int
    student_code: str
    full_name: str | None
    class_name: str | None
    score: Decimal | None
    enrollment_id: int | None = None
    errors: tuple[str, ...] = field(default_factory=tuple)
    warnings: tuple[str, ...] = field(default_factory=tuple)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0


@dataclass(frozen=True)
class ScoreImportPreview:
    """Kết quả Preview; chưa ghi dữ liệu vào database."""

    file_name: str
    assessment_id: int
    rows: tuple[ScoreImportPreviewRow, ...]

    @property
    def total_rows(self) -> int:
        return len(self.rows)

    @property
    def valid_rows(self) -> int:
        return sum(1 for row in self.rows if row.is_valid)

    @property
    def invalid_rows(self) -> int:
        return self.total_rows - self.valid_rows

    @property
    def can_confirm(self) -> bool:
        return self.total_rows > 0 and self.invalid_rows == 0


@dataclass(frozen=True)
class ScoreImportCommitResult:
    """Kết quả sau Confirm và transaction hoàn tất."""

    assessment_id: int
    imported_count: int
    detected_intervention_count: int
