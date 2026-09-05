from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Protocol, runtime_checkable

from models.dto.score_import import (
    ScoreImportContext,
    ScoreImportPreview,
    ScoreImportTemplateStudent,
    ScoreImportWorkbook,
)


@runtime_checkable
class ScoreImportParserContract(Protocol):
    def parse_workbook(self, file_path: str | Path) -> ScoreImportWorkbook:
        ...


@runtime_checkable
class ScoreImportTemplateServiceContract(Protocol):
    def create_template(
        self,
        context: ScoreImportContext,
        roster: Iterable[ScoreImportTemplateStudent],
        output_path: str | Path,
    ) -> Path:
        ...


@runtime_checkable
class ScoreImportPreviewServiceContract(Protocol):
    def preview_import(
        self,
        context: ScoreImportContext,
        workbook: ScoreImportWorkbook,
    ) -> ScoreImportPreview:
        ...
