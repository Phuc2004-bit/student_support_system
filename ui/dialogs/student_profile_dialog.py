from __future__ import annotations

from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QFormLayout,
    QHeaderView,
    QLabel,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from models.dto import StudentProfileData
from services.student_profile_contract import StudentProfileServiceContract
from ui.widgets.enrollment_history_widget import EnrollmentHistoryWidget


def intervention_status_label(status) -> str:
    value = getattr(status, "value", status)
    return {
        "DETECTED": "Đã phát hiện",
        "PLANNED": "Đã lập kế hoạch",
        "IN_PROGRESS": "Đang bổ trợ",
        "WAITING_REVIEW": "Chờ đánh giá",
        "CONTINUE": "Tiếp tục bổ trợ",
        "COMPLETED": "Đã hoàn thành",
    }.get(str(value), str(value))


class StudentProfileDialog(QDialog):
    def __init__(
        self,
        student_id: str,
        profile_service: StudentProfileServiceContract,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.student_id = student_id
        self.profile_service = profile_service
        self.profile: StudentProfileData | None = None

        self.setWindowTitle("Hồ sơ học sinh")
        self.resize(760, 560)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        self.tabs = QTabWidget(self)
        self.tabs.setObjectName("studentProfileTabs")

        self.basic_tab = QWidget(self.tabs)
        basic_form = QFormLayout(self.basic_tab)
        self.student_code_label = QLabel("—", self.basic_tab)
        self.full_name_label = QLabel("—", self.basic_tab)
        self.date_of_birth_label = QLabel("—", self.basic_tab)
        self.gender_label = QLabel("—", self.basic_tab)
        self.phone_label = QLabel("—", self.basic_tab)
        self.email_label = QLabel("—", self.basic_tab)
        self.address_label = QLabel("—", self.basic_tab)
        basic_form.addRow("Mã học sinh", self.student_code_label)
        basic_form.addRow("Họ và tên", self.full_name_label)
        basic_form.addRow("Ngày sinh", self.date_of_birth_label)
        basic_form.addRow("Giới tính", self.gender_label)
        basic_form.addRow("Điện thoại", self.phone_label)
        basic_form.addRow("Email", self.email_label)
        basic_form.addRow("Địa chỉ", self.address_label)

        self.enrollment_history_widget = EnrollmentHistoryWidget(self.tabs)

        self.score_tab = QWidget(self.tabs)
        score_layout = QVBoxLayout(self.score_tab)
        self.score_table = self._build_table(
            ("Lớp", "Môn học", "Bài đánh giá", "Điểm"),
            self.score_tab,
        )
        self.score_table.setObjectName("studentProfileScoreTable")
        score_layout.addWidget(self.score_table)

        self.intervention_tab = QWidget(self.tabs)
        intervention_layout = QVBoxLayout(self.intervention_tab)
        self.intervention_table = self._build_table(
            (
                "Lớp",
                "Môn học",
                "Điểm kích hoạt",
                "Ngày phát hiện",
                "Trạng thái",
                "Hình thức bổ trợ",
            ),
            self.intervention_tab,
        )
        self.intervention_table.setObjectName(
            "studentProfileInterventionTable"
        )
        intervention_layout.addWidget(self.intervention_table)

        self.tabs.addTab(self.basic_tab, "Thông tin cơ bản")
        self.tabs.addTab(self.enrollment_history_widget, "Lịch sử lớp học")
        self.tabs.addTab(self.score_tab, "Lịch sử điểm")
        self.tabs.addTab(self.intervention_tab, "Lịch sử bổ trợ")
        root.addWidget(self.tabs)

    @staticmethod
    def _build_table(
        headers: tuple[str, ...],
        parent: QWidget,
    ) -> QTableWidget:
        table = QTableWidget(parent)
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        table.setSelectionMode(
            QAbstractItemView.SelectionMode.NoSelection
        )
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        return table

    def load_profile(self) -> StudentProfileData:
        profile = self.profile_service.get_profile(self.student_id)
        self.profile = profile
        self._render_basic_information(profile)
        self.enrollment_history_widget.set_history(profile.enrollment_history)
        self._render_scores(profile)
        self._render_interventions(profile)
        return profile

    def _render_basic_information(self, profile: StudentProfileData) -> None:
        student = profile.student
        self.student_code_label.setText(student.student_code)
        self.full_name_label.setText(student.full_name)
        self.date_of_birth_label.setText(
            student.date_of_birth.strftime("%d/%m/%Y")
            if student.date_of_birth
            else "—"
        )
        self.gender_label.setText(student.gender or "—")
        self.phone_label.setText(student.phone or "—")
        self.email_label.setText(student.email or "—")
        self.address_label.setText(student.address or "—")

    def _render_scores(self, profile: StudentProfileData) -> None:
        self.score_table.setRowCount(len(profile.score_history))
        for row, item in enumerate(profile.score_history):
            for column, value in enumerate((
                item.class_name,
                item.subject_name,
                item.assessment_name,
                str(item.score),
            )):
                self.score_table.setItem(row, column, QTableWidgetItem(value))

    def _render_interventions(self, profile: StudentProfileData) -> None:
        self.intervention_table.setRowCount(len(profile.intervention_history))
        for row, item in enumerate(profile.intervention_history):
            for column, value in enumerate((
                item.class_name,
                item.subject_name,
                str(item.trigger_score),
                item.detected_date.strftime("%d/%m/%Y"),
                intervention_status_label(item.status),
                item.support_method or "—",
            )):
                self.intervention_table.setItem(
                    row,
                    column,
                    QTableWidgetItem(value),
                )
