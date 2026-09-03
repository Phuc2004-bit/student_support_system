from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHeaderView,
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
    InterventionPlanningServiceContract,
    InterventionStartServiceContract,
)
from services.user_contract import ResponsibleUserServiceContract
from ui.dialogs.intervention_plan_dialog import InterventionPlanDialog
from ui.dialogs.intervention_start_confirmation import (
    confirm_begin_support,
)
from ui.widgets.dashboard_charts import status_label


def review_result_label(result) -> str:
    value = getattr(result, "value", result)
    return {
        "PASSED": "Đạt ngưỡng",
        "NOT_PASSED": "Chưa đạt ngưỡng",
    }.get(str(value), str(value))


class InterventionDetailDialog(QDialog):
    intervention_planned = Signal(int)
    intervention_started = Signal(int)

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
        user_service: ResponsibleUserServiceContract | None = None,
        plan_dialog_factory=InterventionPlanDialog,
        start_confirmation=confirm_begin_support,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.intervention_id = intervention_id
        self.intervention_service = intervention_service
        self.planning_service = planning_service
        self.start_service = start_service
        self.user_service = user_service
        self.plan_dialog_factory = plan_dialog_factory
        self.start_confirmation = start_confirmation
        self.detail: InterventionDetail | None = None
        self.setObjectName("interventionDetailDialog")
        self.setWindowTitle("Chi tiết hồ sơ bổ trợ")
        self.resize(780, 680)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

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
        root.addWidget(student_group)

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
        root.addWidget(detection_group)

        support_group = QGroupBox("Ca bổ trợ", self)
        support_form = QFormLayout(support_group)
        self.intervention_id_label = QLabel("—", support_group)
        self.status_value_label = QLabel("—", support_group)
        self.start_date_label = QLabel("—", support_group)
        self.responsible_user_label = QLabel("—", support_group)
        self.support_method_label = QLabel("—", support_group)
        self.notes_label = QLabel("—", support_group)
        self.notes_label.setWordWrap(True)
        self.created_at_label = QLabel("—", support_group)
        self.updated_at_label = QLabel("—", support_group)
        support_form.addRow("Mã hồ sơ", self.intervention_id_label)
        support_form.addRow("Trạng thái", self.status_value_label)
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

        review_group = QGroupBox("Lịch sử đánh giá", self)
        review_layout = QVBoxLayout(review_group)
        self.review_empty_label = QLabel(
            "Chưa có lịch sử đánh giá.",
            review_group,
        )
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
        self.close_buttons.rejected.connect(self.reject)
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
