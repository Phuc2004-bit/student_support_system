from __future__ import annotations

from pathlib import Path
from typing import Protocol

from models.dto.data_export import (
    ScoreExportContext,
    ScoreExportData,
    StudentExportContext,
    StudentExportData,
)


class StudentExportServiceContract(Protocol):
    def get_export_data(self, context: StudentExportContext) -> StudentExportData: ...

    def export_xlsx(
        self, context: StudentExportContext, output_path: str | Path
    ) -> Path: ...


class ScoreExportServiceContract(Protocol):
    def get_export_data(self, context: ScoreExportContext) -> ScoreExportData: ...

    def export_xlsx(
        self, context: ScoreExportContext, output_path: str | Path
    ) -> Path: ...
