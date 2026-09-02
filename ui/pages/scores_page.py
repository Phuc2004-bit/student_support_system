from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from ui.widgets.score_context_filter_widget import (
    ScoreContextFilterWidget,
    ScoreContextSelection,
)


class ScoresPage(QWidget):
    def __init__(self, academic_service=None, parent=None):
        super().__init__(parent)
        self.academic_service = academic_service
        self.setObjectName("scoresPage")
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 24)
        root.setSpacing(16)

        self.title_label = QLabel("Điểm & Đánh giá", self)
        self.subtitle_label = QLabel(
            "Chọn đầy đủ ngữ cảnh để xem bảng điểm.",
            self,
        )
        root.addWidget(self.title_label)
        root.addWidget(self.subtitle_label)

        self.context_filter = ScoreContextFilterWidget(
            academic_service=self.academic_service,
            parent=self,
        )
        root.addWidget(self.context_filter)

        self.school_year_combo = self.context_filter.school_year_combo
        self.grade_combo = self.context_filter.grade_combo
        self.class_combo = self.context_filter.class_combo
        self.subject_combo = self.context_filter.subject_combo
        self.assessment_combo = self.context_filter.assessment_combo

        self.context_status_label = QLabel(self)
        root.addWidget(self.context_status_label)

        self.score_table_placeholder = QFrame(self)
        self.score_table_placeholder.setObjectName(
            "scoreTablePlaceholder"
        )
        placeholder_layout = QVBoxLayout(
            self.score_table_placeholder
        )
        self.placeholder_label = QLabel(
            "Bảng điểm sẽ hiển thị tại đây.",
            self.score_table_placeholder,
        )
        self.placeholder_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        placeholder_layout.addWidget(self.placeholder_label)
        root.addWidget(self.score_table_placeholder, 1)

        self.context_filter.context_changed.connect(
            self._on_context_changed
        )
        self._on_context_changed(
            self.context_filter.current_value()
        )

    def initialize_scores(self) -> bool:
        if self.academic_service is None:
            return False
        self.context_filter.load_options()
        return True

    def current_context(self) -> ScoreContextSelection:
        return self.context_filter.current_value()

    def _on_context_changed(
        self,
        context: ScoreContextSelection,
    ) -> None:
        if context.is_complete:
            self.context_status_label.setText(
                "Đã chọn đầy đủ ngữ cảnh."
            )
            self.placeholder_label.setText(
                "Bảng điểm chưa được triển khai trong bước này."
            )
            return

        self.context_status_label.setText(
            "Vui lòng chọn năm học, khối, lớp, môn học "
            "và bài đánh giá."
        )
        self.placeholder_label.setText(
            "Bảng điểm sẽ hiển thị tại đây."
        )
