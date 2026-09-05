from __future__ import annotations

from pathlib import Path
from typing import Protocol

from models.dto.report_export import SupportReportExportData


class ReportExportServiceContract(Protocol):
    def export_xlsx(
        self,
        export_data: SupportReportExportData,
        output_path: str | Path,
    ) -> Path:
        ...
