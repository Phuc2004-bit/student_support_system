from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from models.dto.score_import import ScoreImportIssueSeverity, ScoreImportPreview
from ui.theme import dialog_stylesheet, status_badge_colors


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
        self.setMinimumSize(820, 520)
        self.resize(1040, 620)
        self._build_ui()
        self.setStyleSheet(dialog_stylesheet())
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
        layout.setContentsMargins(24, 22, 24, 24)
        layout.setSpacing(14)
        self.title_label = QLabel("Xem trước dữ liệu nhập điểm", self)
        self.title_label.setProperty("dialogTitle", True)
        self.subtitle_label = QLabel(
            "Kiểm tra từng dòng trước khi xác nhận nhập toàn bộ dữ liệu.",
            self,
        )
        self.subtitle_label.setProperty("dialogSubtitle", True)
        layout.addWidget(self.title_label)
        layout.addWidget(self.subtitle_label)

        self.summary_card = QFrame(self)
        self.summary_card.setObjectName("dialogCard")
        self.summary_card.setProperty("dialogCard", True)
        summary_layout = QVBoxLayout(self.summary_card)
        summary_layout.setContentsMargins(16, 10, 16, 10)
        self.summary_label = QLabel(self.summary_card)
        self.summary_label.setObjectName("scoreImportPreviewSummary")
        summary_layout.addWidget(self.summary_label)
        layout.addWidget(self.summary_card)

        self.table = QTableWidget(self)
        self.table.setObjectName("scoreImportPreviewTable")
        self.table.setColumnCount(len(self.TABLE_HEADERS))
        self.table.setHorizontalHeaderLabels(self.TABLE_HEADERS)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setWordWrap(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(40)
        header = self.table.horizontalHeader()
        header.setMinimumHeight(42)
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table, 1)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self.import_button = QPushButton("Xác nhận nhập", self)
        self.import_button.setObjectName("confirmScoreImportButton")
        self.import_button.setProperty("variant", "primary")
        self.import_button.setEnabled(self.preview.can_commit)
        self.button_box.addButton(
            self.import_button, QDialogButtonBox.ButtonRole.AcceptRole
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.cancel_button = self.button_box.button(
            QDialogButtonBox.StandardButton.Cancel
        )
        self.cancel_button.setText("Hủy")
        self.cancel_button.setProperty("variant", "secondary")
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
                if column == 5:
                    palette_key = (
                        "ERROR" if has_error else "WARNING" if has_warning else "VALID"
                    )
                    foreground, background = status_badge_colors(palette_key)
                    item.setForeground(QColor(foreground))
                    item.setBackground(QColor(background))
                self.table.setItem(index, column, item)
