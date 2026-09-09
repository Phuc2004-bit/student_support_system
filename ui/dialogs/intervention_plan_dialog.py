from __future__ import annotations

from PySide6.QtCore import QDate, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
)

from models.dto import Intervention, InterventionDetail
from services.support_contract import (
    InterventionPlanningServiceContract,
)
from services.user_contract import ResponsibleUserServiceContract
from ui.theme import support_dialog_stylesheet


class InterventionPlanDialog(QDialog):
    plan_saved = Signal(int)

    def __init__(
        self,
        intervention: InterventionDetail,
        support_service: InterventionPlanningServiceContract,
        user_service: ResponsibleUserServiceContract,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.intervention = intervention
        self.support_service = support_service
        self.user_service = user_service
        self.planned_intervention: Intervention | None = None
        self.setObjectName("interventionPlanDialog")
        self.setWindowTitle("Lập kế hoạch bổ trợ")
        self.resize(580, 500)
        self._build_ui()
        self.setStyleSheet(support_dialog_stylesheet())

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(12)

        title = QLabel("Lập kế hoạch bổ trợ", self)
        title.setProperty("dialogTitle", True)
        root.addWidget(title)
        subtitle = QLabel(
            "Phân công người phụ trách và phương pháp hỗ trợ.", self
        )
        subtitle.setProperty("dialogSubtitle", True)
        root.addWidget(subtitle)

        context_card = QFrame(self)
        context_card.setProperty("dialogCard", True)
        context_layout = QHBoxLayout(context_card)
        context_layout.setContentsMargins(16, 12, 16, 12)
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
        context_layout.addWidget(self.student_label, 1)
        context_layout.addWidget(self.context_label)
        root.addWidget(context_card)

        form_card = QFrame(self)
        form_card.setProperty("dialogCard", True)
        form = QFormLayout(form_card)
        form.setContentsMargins(16, 16, 16, 16)
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(12)
        self.responsible_combo = QComboBox(self)
        self.responsible_combo.addItem("Chọn người phụ trách", None)
        self.start_date_input = QDateEdit(self)
        self.start_date_input.setCalendarPopup(True)
        self.start_date_input.setDisplayFormat("dd/MM/yyyy")
        self.start_date_input.setDate(QDate.currentDate())
        self.support_method_input = QLineEdit(self)
        self.support_method_input.setPlaceholderText(
            "Nhập phương pháp hỗ trợ"
        )
        self.notes_input = QTextEdit(self)
        self.notes_input.setPlaceholderText("Ghi chú (không bắt buộc)")

        form.addRow("Người phụ trách", self.responsible_combo)
        form.addRow("Ngày bắt đầu", self.start_date_input)
        form.addRow("Phương pháp", self.support_method_input)
        form.addRow("Ghi chú", self.notes_input)
        root.addWidget(form_card, 1)

        self.error_label = QLabel(self)
        self.error_label.setWordWrap(True)
        self.error_label.setVisible(False)
        root.addWidget(self.error_label)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        self.buttons.accepted.connect(self.save_plan)
        self.buttons.rejected.connect(self.reject)
        save_button = self.buttons.button(
            QDialogButtonBox.StandardButton.Save
        )
        cancel_button = self.buttons.button(
            QDialogButtonBox.StandardButton.Cancel
        )
        if save_button is not None:
            save_button.setText("Lưu kế hoạch")
            save_button.setProperty("variant", "primary")
        if cancel_button is not None:
            cancel_button.setText("Hủy")
        root.addWidget(self.buttons)

    def load_responsible_users(self) -> bool:
        try:
            users = self.user_service.list_active_teachers()
        except Exception:
            self._show_error(
                "Không thể tải danh sách người phụ trách."
            )
            return False

        self.responsible_combo.blockSignals(True)
        self.responsible_combo.clear()
        self.responsible_combo.addItem("Chọn người phụ trách", None)
        for user in users:
            self.responsible_combo.addItem(user.full_name, user.user_id)
        self.responsible_combo.blockSignals(False)
        self.error_label.clear()
        self.error_label.setVisible(False)
        return True

    def save_plan(self) -> bool:
        responsible_user_id = self.responsible_combo.currentData()
        if responsible_user_id is None:
            self._show_error("Vui lòng chọn người phụ trách.")
            return False

        qdate = self.start_date_input.date()
        start_date = qdate.toPython()
        support_method = self.support_method_input.text().strip() or None
        notes = self.notes_input.toPlainText().strip() or None

        try:
            planned = self.support_service.plan_intervention(
                intervention_id=self.intervention.intervention_id,
                responsible_user_id=responsible_user_id,
                start_date=start_date,
                support_method=support_method,
                notes=notes,
            )
        except Exception:
            self._show_error(
                "Không thể lưu kế hoạch bổ trợ. Vui lòng thử lại."
            )
            return False

        self.planned_intervention = planned
        self.plan_saved.emit(planned.intervention_id)
        self.accept()
        return True

    def _show_error(self, message: str) -> None:
        self.error_label.setText(message)
        self.error_label.setVisible(True)
