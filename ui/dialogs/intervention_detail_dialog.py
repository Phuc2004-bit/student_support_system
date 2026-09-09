from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QFormLayout,
    QGroupBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from models.dto import InterventionDetail
from services.support_read_contract import (
    InterventionDetailServiceContract,
)
from services.support_contract import (
    InterventionContinueServiceContract,
    InterventionPlanningServiceContract,
    InterventionReviewServiceContract,
    InterventionStartServiceContract,
    InterventionWaitingReviewServiceContract,
)
from services.user_contract import ResponsibleUserServiceContract
from ui.dialogs.intervention_plan_dialog import InterventionPlanDialog
from ui.dialogs.intervention_review_dialog import InterventionReviewDialog
from ui.dialogs.intervention_continue_confirmation import (
    confirm_continue_support,
)
from ui.dialogs.intervention_start_confirmation import (
    confirm_begin_support,
)
from ui.dialogs.intervention_waiting_review_confirmation import (
    confirm_ready_for_review,
)
from ui.widgets.dashboard_charts import status_label
from ui.theme import support_dialog_stylesheet


def review_result_label(result) -> str:
    value = getattr(result, "value", result)
    return {
        "PASSED": "Đạt ngưỡng",
        "NOT_PASSED": "Chưa đạt ngưỡng",
    }.get(str(value), str(value))


class InterventionDetailDialog(QDialog):
    intervention_planned = Signal(int)
    intervention_started = Signal(int)
    intervention_waiting_review = Signal(int)
    intervention_reviewed = Signal(int)
    intervention_continued = Signal(int)

    REVIEW_HEADERS = (
        "Ngày đánh giá",
        "Điểm",
        "Kết quả",
        "Ghi chú",
    )

    def __init__(
        self,
        intervention_id: int,
        intervention_service: InterventionDetailServiceContract,
        planning_service: InterventionPlanningServiceContract | None = None,
        start_service: InterventionStartServiceContract | None = None,
        waiting_review_service:
            InterventionWaitingReviewServiceContract | None = None,
        review_service: InterventionReviewServiceContract | None = None,
        continue_service: InterventionContinueServiceContract | None = None,
        assessment_service=None,
        user_service: ResponsibleUserServiceContract | None = None,
        plan_dialog_factory=InterventionPlanDialog,
        start_confirmation=confirm_begin_support,
        waiting_review_confirmation=confirm_ready_for_review,
        review_dialog_factory=InterventionReviewDialog,
        continue_confirmation=confirm_continue_support,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.intervention_id = intervention_id
        self.intervention_service = intervention_service
        self.planning_service = planning_service
        self.start_service = start_service
        self.waiting_review_service = waiting_review_service
        self.review_service = review_service
        self.continue_service = continue_service
        self.assessment_service = assessment_service
        self.user_service = user_service
        self.plan_dialog_factory = plan_dialog_factory
        self.start_confirmation = start_confirmation
        self.waiting_review_confirmation = waiting_review_confirmation
        self.review_dialog_factory = review_dialog_factory
        self.continue_confirmation = continue_confirmation
        self.detail: InterventionDetail | None = None
        self.setObjectName("interventionDetailDialog")
        self.setWindowTitle("Chi tiết hồ sơ bổ trợ")
        self.resize(920, 720)
        self._build_ui()
        self.setStyleSheet(support_dialog_stylesheet())

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(12)

        self.dialog_title_label = QLabel("Chi tiết hồ sơ bổ trợ", self)
        self.dialog_title_label.setProperty("dialogTitle", True)
        root.addWidget(self.dialog_title_label)

        self.identity_card = QFrame(self)
        self.identity_card.setObjectName("interventionIdentityCard")
        identity_layout = QHBoxLayout(self.identity_card)
        identity_layout.setContentsMargins(16, 12, 16, 12)
        identity_text = QVBoxLayout()
        self.identity_name_label = QLabel("Chưa tải hồ sơ", self.identity_card)
        self.identity_name_label.setObjectName("interventionStudentName")
        self.identity_context_label = QLabel("—", self.identity_card)
        self.identity_context_label.setObjectName("interventionStudentContext")
        identity_text.addWidget(self.identity_name_label)
        identity_text.addWidget(self.identity_context_label)
        identity_layout.addLayout(identity_text, 1)
        self.status_value_label = QLabel("—", self.identity_card)
        self.status_value_label.setObjectName("interventionStatusBadge")
        self.status_value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        identity_layout.addWidget(self.status_value_label)
        root.addWidget(self.identity_card)

        self.workflow_card = QFrame(self)
        self.workflow_card.setObjectName("interventionWorkflowCard")
        workflow_layout = QVBoxLayout(self.workflow_card)
        workflow_layout.setContentsMargins(14, 12, 14, 12)
        workflow_layout.setSpacing(8)
        workflow_header = QLabel("TIẾN TRÌNH BỔ TRỢ", self.workflow_card)
        workflow_header.setProperty("dialogSubtitle", True)
        workflow_layout.addWidget(workflow_header)
        workflow_steps_layout = QHBoxLayout()
        workflow_steps_layout.setSpacing(6)
        self.workflow_step_labels = []
        for text in (
            "Mới phát hiện",
            "Đã lập kế hoạch",
            "Đang bổ trợ",
            "Chờ đánh giá",
            "Kết quả",
        ):
            label = QLabel(text, self.workflow_card)
            label.setProperty("workflowStep", True)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            workflow_steps_layout.addWidget(label, 1)
            self.workflow_step_labels.append(label)
        workflow_layout.addLayout(workflow_steps_layout)
        self.workflow_message_label = QLabel(
            "Chọn hồ sơ để xem tiến trình.", self.workflow_card
        )
        self.workflow_message_label.setObjectName(
            "interventionWorkflowMessage"
        )
        workflow_layout.addWidget(self.workflow_message_label)
        root.addWidget(self.workflow_card)

        self.error_label = QLabel(self)
        self.error_label.setObjectName("interventionDetailError")
        self.error_label.setWordWrap(True)
        self.error_label.setVisible(False)
        root.addWidget(self.error_label)

        student_group = QGroupBox("Học sinh", self)
        student_form = QFormLayout(student_group)
        self.student_code_label = QLabel("—", student_group)
        self.full_name_label = QLabel("—", student_group)
        self.grade_label = QLabel("—", student_group)
        self.class_label = QLabel("—", student_group)
        self.school_year_label = QLabel("—", student_group)
        student_form.addRow("Mã học sinh", self.student_code_label)
        student_form.addRow("Họ và tên", self.full_name_label)
        student_form.addRow("Khối", self.grade_label)
        student_form.addRow("Lớp", self.class_label)
        student_form.addRow("Năm học", self.school_year_label)
        context_row = QHBoxLayout()
        context_row.setSpacing(12)
        context_row.addWidget(student_group, 1)

        detection_group = QGroupBox("Môn học và phát hiện", self)
        detection_form = QFormLayout(detection_group)
        self.subject_label = QLabel("—", detection_group)
        self.trigger_assessment_label = QLabel("—", detection_group)
        self.trigger_score_label = QLabel("—", detection_group)
        self.detected_date_label = QLabel("—", detection_group)
        detection_form.addRow("Môn học", self.subject_label)
        detection_form.addRow(
            "Bài đánh giá nguồn",
            self.trigger_assessment_label,
        )
        detection_form.addRow(
            "Điểm phát hiện",
            self.trigger_score_label,
        )
        detection_form.addRow(
            "Ngày phát hiện",
            self.detected_date_label,
        )
        context_row.addWidget(detection_group, 1)
        root.addLayout(context_row)

        support_group = QGroupBox("Ca bổ trợ", self)
        support_form = QFormLayout(support_group)
        self.intervention_id_label = QLabel("—", support_group)
        self.start_date_label = QLabel("—", support_group)
        self.responsible_user_label = QLabel("—", support_group)
        self.support_method_label = QLabel("—", support_group)
        self.notes_label = QLabel("—", support_group)
        self.notes_label.setWordWrap(True)
        self.created_at_label = QLabel("—", support_group)
        self.updated_at_label = QLabel("—", support_group)
        support_form.addRow("Mã hồ sơ", self.intervention_id_label)
        support_form.addRow("Ngày bắt đầu", self.start_date_label)
        support_form.addRow(
            "Người phụ trách",
            self.responsible_user_label,
        )
        support_form.addRow("Phương pháp", self.support_method_label)
        support_form.addRow("Ghi chú", self.notes_label)
        support_form.addRow("Ngày tạo", self.created_at_label)
        support_form.addRow("Cập nhật lần cuối", self.updated_at_label)
        root.addWidget(support_group)

        self.outcome_message_label = QLabel(self)
        self.outcome_message_label.setWordWrap(True)
        self.outcome_message_label.setVisible(False)
        root.addWidget(self.outcome_message_label)

        review_group = QGroupBox("Lịch sử đánh giá", self)
        review_layout = QVBoxLayout(review_group)
        self.review_empty_label = QLabel(
            "Chưa có lịch sử đánh giá.",
            review_group,
        )
        self.review_empty_label.setObjectName("interventionReviewEmpty")
        review_layout.addWidget(self.review_empty_label)
        self.review_table = QTableWidget(review_group)
        self.review_table.setObjectName("interventionReviewTable")
        self.review_table.setColumnCount(len(self.REVIEW_HEADERS))
        self.review_table.setHorizontalHeaderLabels(self.REVIEW_HEADERS)
        self.review_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.review_table.setSelectionMode(
            QAbstractItemView.SelectionMode.NoSelection
        )
        self.review_table.verticalHeader().setVisible(False)
        self.review_table.verticalHeader().setDefaultSectionSize(38)
        self.review_table.setShowGrid(False)
        self.review_table.setAlternatingRowColors(True)
        self.review_table.horizontalHeader().setMinimumHeight(40)
        self.review_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        review_layout.addWidget(self.review_table)
        root.addWidget(review_group, 1)

        self.close_buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close,
            parent=self,
        )
        self.plan_button = self.close_buttons.addButton(
            "Lập kế hoạch",
            QDialogButtonBox.ButtonRole.ActionRole,
        )
        self.plan_button.setVisible(False)
        self.plan_button.clicked.connect(self.open_plan_dialog)
        self.start_button = self.close_buttons.addButton(
            "Bắt đầu bổ trợ",
            QDialogButtonBox.ButtonRole.ActionRole,
        )
        self.start_button.setVisible(False)
        self.start_button.clicked.connect(self.begin_planned_support)
        self.waiting_review_button = self.close_buttons.addButton(
            "Chuyển chờ đánh giá",
            QDialogButtonBox.ButtonRole.ActionRole,
        )
        self.waiting_review_button.setVisible(False)
        self.waiting_review_button.clicked.connect(
            self.move_to_review_queue
        )
        self.review_button = self.close_buttons.addButton(
            "Đánh giá",
            QDialogButtonBox.ButtonRole.ActionRole,
        )
        self.review_button.setVisible(False)
        self.review_button.clicked.connect(self.open_review_dialog)
        self.continue_button = self.close_buttons.addButton(
            "Tiếp tục bổ trợ",
            QDialogButtonBox.ButtonRole.ActionRole,
        )
        self.continue_button.setVisible(False)
        self.continue_button.clicked.connect(self.resume_support)
        self.close_buttons.rejected.connect(self.reject)
        close_button = self.close_buttons.button(
            QDialogButtonBox.StandardButton.Close
        )
        if close_button is not None:
            close_button.setText("Đóng")
        root.addWidget(self.close_buttons)

    def load_detail(self) -> InterventionDetail | None:
        try:
            detail = self.intervention_service.get_intervention_detail(
                self.intervention_id
            )
        except Exception:
            self.detail = None
            self.error_label.setText(
                "Không thể tải chi tiết hồ sơ bổ trợ."
            )
            self.error_label.setVisible(True)
            return None

        self.detail = detail
        self.error_label.clear()
        self.error_label.setVisible(False)
        self._render_detail(detail)
        return detail

    def _render_detail(self, detail: InterventionDetail) -> None:
        self.identity_name_label.setText(detail.full_name)
        identity_context = [detail.student_code, detail.class_name]
        if detail.school_year_name:
            identity_context.append(detail.school_year_name)
        identity_context.append(detail.subject_name)
        self.identity_context_label.setText("  •  ".join(identity_context))
        self.student_code_label.setText(detail.student_code)
        self.full_name_label.setText(detail.full_name)
        self.grade_label.setText(
            f"Khối {detail.grade_number}"
            if detail.grade_number is not None
            else "—"
        )
        self.class_label.setText(detail.class_name)
        self.school_year_label.setText(
            detail.school_year_name or "—"
        )
        self.subject_label.setText(detail.subject_name)
        self.trigger_assessment_label.setText(
            detail.trigger_assessment_name or "—"
        )
        self.trigger_score_label.setText(str(detail.trigger_score))
        self.detected_date_label.setText(
            detail.detected_date.strftime("%d/%m/%Y")
        )
        self.intervention_id_label.setText(str(detail.intervention_id))
        status = getattr(detail.status, "value", detail.status)
        self.status_value_label.setText(status_label(str(status)))
        self.status_value_label.setProperty("interventionStatus", str(status))
        self.status_value_label.style().unpolish(self.status_value_label)
        self.status_value_label.style().polish(self.status_value_label)
        self._render_workflow(str(status))
        self.start_date_label.setText(
            detail.start_date.strftime("%d/%m/%Y")
            if detail.start_date is not None
            else "—"
        )
        self.responsible_user_label.setText(
            detail.responsible_user_name or "—"
        )
        self.support_method_label.setText(
            detail.support_method or "—"
        )
        self.notes_label.setText(detail.notes or "—")
        self.created_at_label.setText(
            detail.created_at.strftime("%d/%m/%Y %H:%M")
        )
        self.updated_at_label.setText(
            detail.updated_at.strftime("%d/%m/%Y %H:%M")
        )
        self._render_reviews(detail)
        can_plan = (
            detail.status.value == "DETECTED"
            and self.planning_service is not None
            and self.user_service is not None
        )
        self.plan_button.setVisible(can_plan)
        self.plan_button.setEnabled(can_plan)
        can_start = (
            detail.status.value == "PLANNED"
            and self.start_service is not None
        )
        self.start_button.setVisible(can_start)
        self.start_button.setEnabled(can_start)
        can_wait_for_review = (
            detail.status.value == "IN_PROGRESS"
            and self.waiting_review_service is not None
        )
        self.waiting_review_button.setVisible(can_wait_for_review)
        self.waiting_review_button.setEnabled(can_wait_for_review)
        can_review = (
            detail.status.value == "WAITING_REVIEW"
            and self.review_service is not None
            and self.assessment_service is not None
        )
        self.review_button.setVisible(can_review)
        self.review_button.setEnabled(can_review)
        can_continue = (
            detail.status.value == "CONTINUE"
            and self.continue_service is not None
        )
        self.continue_button.setVisible(can_continue)
        self.continue_button.setEnabled(can_continue)
        self._render_outcome_message(str(status))
        for button in (
            self.plan_button,
            self.start_button,
            self.waiting_review_button,
            self.review_button,
            self.continue_button,
        ):
            button.setProperty("variant", "primary")
            button.style().unpolish(button)
            button.style().polish(button)

    def _render_workflow(self, status: str) -> None:
        step_index = {
            "DETECTED": 0,
            "PLANNED": 1,
            "IN_PROGRESS": 2,
            "WAITING_REVIEW": 3,
            "CONTINUE": 4,
            "COMPLETED": 4,
        }.get(status, 0)
        for index, label in enumerate(self.workflow_step_labels):
            state = "upcoming"
            prefix = "○"
            if index < step_index:
                state = "done"
                prefix = "✓"
            elif index == step_index:
                state = "current"
                prefix = "●"
            if status == "CONTINUE" and index == 4:
                state = "attention"
            elif status == "COMPLETED" and index == 4:
                state = "complete"
            base_text = (
                "Mới phát hiện",
                "Đã lập kế hoạch",
                "Đang bổ trợ",
                "Chờ đánh giá",
                "Kết quả",
            )[index]
            label.setText(f"{prefix} {base_text}")
            label.setProperty("workflowState", state)
            label.style().unpolish(label)
            label.style().polish(label)

        self.workflow_message_label.setText({
            "DETECTED": "Hồ sơ mới phát hiện, sẵn sàng lập kế hoạch.",
            "PLANNED": "Kế hoạch đã được lưu, sẵn sàng bắt đầu bổ trợ.",
            "IN_PROGRESS": "Học sinh đang trong quá trình bổ trợ.",
            "WAITING_REVIEW": "Hồ sơ đang chờ đánh giá lại.",
            "CONTINUE": "Cần tiếp tục bổ trợ.",
            "COMPLETED": "Đã đạt ngưỡng qua quy trình đánh giá.",
        }.get(status, "Trạng thái hồ sơ đã được cập nhật."))

    def _render_outcome_message(self, status: str) -> None:
        messages = {
            "CONTINUE": (
                "interventionContinueMessage",
                "Kết quả đánh giá cho thấy học sinh cần tiếp tục bổ trợ.",
            ),
            "COMPLETED": (
                "interventionCompletedMessage",
                "Không còn thao tác bổ trợ. Hồ sơ đã đạt ngưỡng.",
            ),
        }
        if status not in messages:
            self.outcome_message_label.setVisible(False)
            return
        object_name, message = messages[status]
        self.outcome_message_label.setObjectName(object_name)
        self.outcome_message_label.setText(message)
        self.outcome_message_label.setVisible(True)

    def open_plan_dialog(self) -> bool:
        if (
            self.detail is None
            or self.detail.status.value != "DETECTED"
            or self.planning_service is None
            or self.user_service is None
        ):
            return False

        dialog = self.plan_dialog_factory(
            intervention=self.detail,
            support_service=self.planning_service,
            user_service=self.user_service,
            parent=self,
        )
        dialog.load_responsible_users()
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return False

        refreshed = self.load_detail()
        if refreshed is None:
            return False
        self.intervention_planned.emit(self.intervention_id)
        return True

    def begin_planned_support(self) -> bool:
        if (
            self.detail is None
            or self.detail.status.value != "PLANNED"
            or self.start_service is None
        ):
            return False

        try:
            started = self.start_confirmation(
                self,
                self.start_service,
                self.intervention_id,
            )
        except Exception:
            self.error_label.setText(
                "Không thể bắt đầu bổ trợ. Vui lòng thử lại."
            )
            self.error_label.setVisible(True)
            return False

        if not started:
            return False

        refreshed = self.load_detail()
        if refreshed is None:
            return False
        self.intervention_started.emit(self.intervention_id)
        return True

    def move_to_review_queue(self) -> bool:
        if (
            self.detail is None
            or self.detail.status.value != "IN_PROGRESS"
            or self.waiting_review_service is None
        ):
            return False

        try:
            moved = self.waiting_review_confirmation(
                self,
                self.waiting_review_service,
                self.intervention_id,
            )
        except Exception:
            self.error_label.setText(
                "Không thể chuyển hồ sơ sang chờ đánh giá. "
                "Vui lòng thử lại."
            )
            self.error_label.setVisible(True)
            return False

        if not moved:
            return False

        refreshed = self.load_detail()
        if refreshed is None:
            return False
        self.intervention_waiting_review.emit(self.intervention_id)
        return True

    def open_review_dialog(self) -> bool:
        if (
            self.detail is None
            or self.detail.status.value != "WAITING_REVIEW"
            or self.review_service is None
            or self.assessment_service is None
        ):
            return False

        dialog = self.review_dialog_factory(
            intervention=self.detail,
            support_service=self.review_service,
            assessment_service=self.assessment_service,
            parent=self,
        )
        if not dialog.load_assessments():
            return False
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return False

        refreshed = self.load_detail()
        if refreshed is None:
            return False
        self.intervention_reviewed.emit(self.intervention_id)
        return True

    def resume_support(self) -> bool:
        if (
            self.detail is None
            or self.detail.status.value != "CONTINUE"
            or self.continue_service is None
        ):
            return False

        try:
            continued = self.continue_confirmation(
                self,
                self.continue_service,
                self.intervention_id,
            )
        except Exception:
            self.error_label.setText(
                "Không thể tiếp tục bổ trợ. Vui lòng thử lại."
            )
            self.error_label.setVisible(True)
            return False

        if not continued:
            return False

        refreshed = self.load_detail()
        if refreshed is None:
            return False
        self.intervention_continued.emit(self.intervention_id)
        return True

    def _render_reviews(self, detail: InterventionDetail) -> None:
        reviews = detail.reviews
        self.review_table.setRowCount(len(reviews))
        for row, review in enumerate(reviews):
            values = (
                review.review_date.strftime("%d/%m/%Y"),
                str(review.score) if review.score is not None else "—",
                review_result_label(review.result),
                review.notes or "—",
            )
            for column, value in enumerate(values):
                self.review_table.setItem(
                    row,
                    column,
                    QTableWidgetItem(value),
                )

        has_reviews = bool(reviews)
        self.review_empty_label.setVisible(not has_reviews)
        self.review_table.setVisible(has_reviews)
