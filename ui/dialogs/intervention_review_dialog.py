from __future__ import annotations

from PySide6.QtCore import QDate, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
)

from models.dto import Intervention, InterventionDetail
from models.enums import AssessmentStatus
from services.assessment_contract import AssessmentReadServiceContract
from services.support_contract import InterventionReviewServiceContract


class InterventionReviewDialog(QDialog):
    review_saved = Signal(int)

    def __init__(
        self,
        intervention: InterventionDetail,
        support_service: InterventionReviewServiceContract,
        assessment_service: AssessmentReadServiceContract,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.intervention = intervention
        self.support_service = support_service
        self.assessment_service = assessment_service
        self.reviewed_intervention: Intervention | None = None
        self.setObjectName("interventionReviewDialog")
        self.setWindowTitle("Đánh giá bổ trợ")
        self.resize(520, 420)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        form = QFormLayout()

        self.student_label = QLabel(
            f"{self.intervention.student_code} — "
            f"{self.intervention.full_name}",
            self,
        )
        self.context_label = QLabel(
            f"{self.intervention.class_name} — "
            f"{self.intervention.subject_name}",
            self,
        )
        self.trigger_score_label = QLabel(
            str(self.intervention.trigger_score),
            self,
        )
        self.status_label = QLabel("Chờ đánh giá", self)
        self.assessment_combo = QComboBox(self)
        self.assessment_combo.addItem("Chọn bài đánh giá", None)
        self.score_input = QLineEdit(self)
        self.score_input.setPlaceholderText("Nhập điểm từ 0 đến 10")
        self.review_date_input = QDateEdit(self)
        self.review_date_input.setCalendarPopup(True)
        self.review_date_input.setDisplayFormat("dd/MM/yyyy")
        self.review_date_input.setDate(QDate.currentDate())
        self.notes_input = QTextEdit(self)
        self.notes_input.setPlaceholderText("Ghi chú (không bắt buộc)")

        form.addRow("Học sinh", self.student_label)
        form.addRow("Lớp / Môn", self.context_label)
        form.addRow("Điểm phát hiện", self.trigger_score_label)
        form.addRow("Trạng thái", self.status_label)
        form.addRow("Bài đánh giá", self.assessment_combo)
        form.addRow("Điểm đánh giá", self.score_input)
        form.addRow("Ngày đánh giá", self.review_date_input)
        form.addRow("Ghi chú", self.notes_input)
        root.addLayout(form)

        self.error_label = QLabel(self)
        self.error_label.setWordWrap(True)
        self.error_label.setVisible(False)
        root.addWidget(self.error_label)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        self.buttons.accepted.connect(self.save_review)
        self.buttons.rejected.connect(self.reject)
        root.addWidget(self.buttons)

    def load_assessments(self) -> bool:
        if self.intervention.school_year_id is None:
            self._show_error("Hồ sơ chưa có ngữ cảnh năm học hợp lệ.")
            return False
        try:
            assessments = self.assessment_service.list_assessments(
                school_year_id=self.intervention.school_year_id,
                subject_id=self.intervention.subject_id,
                status=AssessmentStatus.ACTIVE,
            )
        except Exception:
            self._show_error("Không thể tải danh sách bài đánh giá.")
            return False

        self.assessment_combo.clear()
        self.assessment_combo.addItem("Chọn bài đánh giá", None)
        for assessment in assessments:
            self.assessment_combo.addItem(
                assessment.assessment_name,
                assessment.assessment_id,
            )
        self.error_label.clear()
        self.error_label.setVisible(False)
        return True

    def save_review(self) -> bool:
        assessment_id = self.assessment_combo.currentData()
        if assessment_id is None:
            self._show_error("Vui lòng chọn bài đánh giá.")
            return False

        score_value = self.score_input.text().strip()
        if not score_value:
            self._show_error("Vui lòng nhập điểm đánh giá.")
            return False

        try:
            reviewed = self.support_service.review_intervention(
                intervention_id=self.intervention.intervention_id,
                review_date=self.review_date_input.date().toPython(),
                notes=self.notes_input.toPlainText().strip() or None,
                assessment_id=assessment_id,
                score_value=score_value,
            )
        except Exception:
            self._show_error(
                "Không thể lưu đánh giá. Vui lòng kiểm tra dữ liệu "
                "và thử lại."
            )
            return False

        self.reviewed_intervention = reviewed
        self.review_saved.emit(reviewed.intervention_id)
        self.accept()
        return True

    def _show_error(self, message: str) -> None:
        self.error_label.setText(message)
        self.error_label.setVisible(True)
