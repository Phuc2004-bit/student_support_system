from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from models.dto.score_import import ScoreImportIssueSeverity, ScoreImportPreview


class ScoreImportPreviewDialog(QDialog):
    TABLE_HEADERS = (
        "Dòng Excel",
        "Mã học sinh",
        "Họ tên Excel",
        "Họ tên hệ thống",
        "Điểm",
        "Trạng thái",
        "Lỗi / Cảnh báo",
    )

    def __init__(self, preview: ScoreImportPreview, parent: QWidget | None = None):
        super().__init__(parent)
        self.preview = preview
        self.setObjectName("scoreImportPreviewDialog")
        self.setWindowTitle("Xem trước nhập điểm từ Excel")
        self.resize(980, 560)
        self._build_ui()
        self._render()

    @property
    def warning_count(self) -> int:
        return sum(
            any(
                issue.severity == ScoreImportIssueSeverity.WARNING
                for issue in row.issues
            )
            for row in self.preview.rows
        )

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        self.summary_label = QLabel(self)
        self.summary_label.setObjectName("scoreImportPreviewSummary")
        layout.addWidget(self.summary_label)

        self.table = QTableWidget(self)
        self.table.setObjectName("scoreImportPreviewTable")
        self.table.setColumnCount(len(self.TABLE_HEADERS))
        self.table.setHorizontalHeaderLabels(self.TABLE_HEADERS)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table, 1)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self.import_button = QPushButton("Xác nhận nhập", self)
        self.import_button.setObjectName("confirmScoreImportButton")
        self.import_button.setEnabled(self.preview.can_commit)
        self.button_box.addButton(
            self.import_button, QDialogButtonBox.ButtonRole.AcceptRole
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def _render(self) -> None:
        self.summary_label.setText(
            f"Tổng dòng: {len(self.preview.rows)} | "
            f"Hợp lệ: {self.preview.valid_count} | "
            f"Lỗi: {self.preview.invalid_count} | "
            f"Cảnh báo: {self.warning_count}"
        )
        self.table.setRowCount(len(self.preview.rows))
        for index, row in enumerate(self.preview.rows):
            has_error = any(issue.is_blocking for issue in row.issues)
            has_warning = any(
                issue.severity == ScoreImportIssueSeverity.WARNING
                for issue in row.issues
            )
            status = "Lỗi" if has_error else "Cảnh báo" if has_warning else "Hợp lệ"
            issue_text = "\n".join(
                ("[Cảnh báo] " if issue.severity == ScoreImportIssueSeverity.WARNING else "[Lỗi] ")
                + issue.message
                for issue in row.issues
            )
            values = (
                str(row.row_number),
                row.student_id,
                row.student_name_excel or "-",
                row.student_name_db or "-",
                str(row.normalized_score) if row.normalized_score is not None else "-",
                status,
                issue_text or "-",
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column in (0, 4, 5):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(index, column, item)
