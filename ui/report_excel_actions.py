from __future__ import annotations

from PySide6.QtWidgets import QFileDialog, QMessageBox, QPushButton

from exceptions import ReportExportError, ValidationError
from models.dto.report_export import SupportReportExportData


class ReportExcelActions:
    def _configure_excel_actions(self, writer) -> None:
        self.report_export_service = writer

    def _add_excel_action(self, layout) -> None:
        self.export_button = QPushButton("Xuất Excel", self)
        self.export_button.setObjectName("exportReportsExcelButton")
        layout.addWidget(self.export_button)

    def _connect_excel_action(self) -> None:
        self.export_button.clicked.connect(
            lambda _checked=False: self.export_report()
        )

    def export_report(self) -> bool:
        filters = self.current_filters()
        context = self.filter_widget.export_context()
        if context is None:
            self.state_label.setText(
                "Vui lòng chọn năm học để xuất báo cáo."
            )
            return False
        if self.report_export_service is None:
            self._show_export_error("Chưa có dịch vụ xuất báo cáo Excel.")
            return False
        if self.report_data is None or (
            self._report_filters is not None
            and self._report_filters != filters
        ):
            if not self.refresh_report():
                return False
        snapshot = self.report_data
        if snapshot is None:
            return False
        output_path, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "Xuất báo cáo bổ trợ",
            "bao_cao_bo_tro.xlsx",
            "Excel Workbook (*.xlsx)",
        )
        if not output_path:
            return False
        if not output_path.lower().endswith(".xlsx"):
            output_path += ".xlsx"
        try:
            self.report_export_service.export_xlsx(
                SupportReportExportData(context=context, report=snapshot),
                output_path,
            )
        except Exception as exc:
            self._show_export_error(self._export_error_message(exc))
            return False
        QMessageBox.information(
            self,
            "Xuất Excel",
            "Đã xuất báo cáo Excel thành công.",
        )
        return True

    def _show_export_error(self, message: str) -> None:
        self.state_label.setText(message)
        QMessageBox.warning(self, "Xuất báo cáo Excel", message)

    @staticmethod
    def _export_error_message(exc: Exception) -> str:
        if isinstance(exc, (ReportExportError, ValidationError)):
            return str(exc)
        return "Không thể xuất báo cáo Excel. Vui lòng thử lại."
