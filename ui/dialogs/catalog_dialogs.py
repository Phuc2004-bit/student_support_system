from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QFormLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from models.dto import (
    Assessment,
    Grade,
    SchoolClass,
    SchoolYear,
    Subject,
    SupportRule,
)
from models.enums import AssessmentStatus
from ui.theme import dialog_stylesheet


def _python_date(value: QDate) -> date:
    return date(value.year(), value.month(), value.day())


def _qt_date(value: date) -> QDate:
    return QDate(value.year, value.month, value.day)


def _build_dialog_shell(
    dialog: QDialog,
    form: QFormLayout,
    buttons: QDialogButtonBox,
    title: str,
    subtitle: str,
) -> None:
    dialog.resize(520, dialog.sizeHint().height())
    title_label = QLabel(title, dialog)
    title_label.setProperty("dialogTitle", True)
    subtitle_label = QLabel(subtitle, dialog)
    subtitle_label.setProperty("dialogSubtitle", True)
    subtitle_label.setWordWrap(True)
    card = QFrame(dialog)
    card.setProperty("dialogCard", True)
    card.setLayout(form)
    form.setContentsMargins(20, 18, 20, 18)
    form.setHorizontalSpacing(18)
    form.setVerticalSpacing(12)
    form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
    save_button = buttons.button(QDialogButtonBox.StandardButton.Save)
    cancel_button = buttons.button(QDialogButtonBox.StandardButton.Cancel)
    save_button.setText("Lưu")
    cancel_button.setText("Hủy")
    save_button.setProperty("variant", "primary")
    root = QVBoxLayout(dialog)
    root.setContentsMargins(28, 24, 28, 24)
    root.setSpacing(14)
    root.addWidget(title_label)
    root.addWidget(subtitle_label)
    root.addWidget(card)
    root.addWidget(buttons)
    dialog.title_label = title_label
    dialog.subtitle_label = subtitle_label
    dialog.form_card = card
    dialog.save_button = save_button
    dialog.cancel_button = cancel_button
    dialog.setStyleSheet(dialog_stylesheet())


class SchoolYearDialog(QDialog):
    def __init__(
        self,
        school_year: SchoolYear | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.school_year = school_year
        self.setWindowTitle(
            "Sửa năm học" if school_year else "Thêm năm học"
        )
        form = QFormLayout()
        self.year_name_input = QLineEdit(self)
        self.year_name_input.setMaxLength(20)
        self.start_date_input = QDateEdit(self)
        self.end_date_input = QDateEdit(self)
        for control in (self.start_date_input, self.end_date_input):
            control.setCalendarPopup(True)
            control.setDisplayFormat("dd/MM/yyyy")
        today = QDate.currentDate()
        self.start_date_input.setDate(today)
        self.end_date_input.setDate(today.addMonths(9))
        self.current_checkbox = QCheckBox("Năm học hiện tại", self)
        form.addRow("Tên năm học *", self.year_name_input)
        form.addRow("Ngày bắt đầu *", self.start_date_input)
        form.addRow("Ngày kết thúc *", self.end_date_input)
        form.addRow("", self.current_checkbox)
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        _build_dialog_shell(
            self, form, self.button_box, self.windowTitle(),
            "Khai báo thời gian và trạng thái năm học.",
        )
        if school_year is not None:
            self.year_name_input.setText(school_year.year_name)
            if school_year.start_date is not None:
                self.start_date_input.setDate(_qt_date(school_year.start_date))
            if school_year.end_date is not None:
                self.end_date_input.setDate(_qt_date(school_year.end_date))
            self.current_checkbox.setChecked(school_year.is_current)

    def values(self) -> tuple[str, date, date, bool]:
        return (
            self.year_name_input.text(),
            _python_date(self.start_date_input.date()),
            _python_date(self.end_date_input.date()),
            self.current_checkbox.isChecked(),
        )


class GradeDialog(QDialog):
    def __init__(
        self,
        grade: Grade | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.grade = grade
        self.setWindowTitle("Sửa khối" if grade else "Thêm khối")
        self.grade_number_input = QSpinBox(self)
        self.grade_number_input.setRange(6, 12)
        self.grade_name_input = QLineEdit(self)
        self.grade_name_input.setMaxLength(30)
        form = QFormLayout()
        form.addRow("Số khối *", self.grade_number_input)
        form.addRow("Tên hiển thị", self.grade_name_input)
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        _build_dialog_shell(
            self, form, self.button_box, self.windowTitle(),
            "Thiết lập tên hiển thị cho khối lớp.",
        )
        if grade is not None:
            self.grade_number_input.setValue(grade.grade_number)
            self.grade_number_input.setEnabled(False)
            self.grade_name_input.setText(grade.grade_name or "")

    def values(self) -> tuple[int, str | None]:
        return (
            self.grade_number_input.value(),
            self.grade_name_input.text() or None,
        )


class ClassDialog(QDialog):
    def __init__(
        self,
        school_years: list[SchoolYear],
        grades: list[Grade],
        school_class: SchoolClass | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.school_class = school_class
        self.setWindowTitle("Sửa lớp" if school_class else "Thêm lớp")
        self.class_name_input = QLineEdit(self)
        self.class_name_input.setMaxLength(30)
        self.school_year_combo = QComboBox(self)
        self.grade_combo = QComboBox(self)
        self.teacher_input = QLineEdit(self)
        self.teacher_input.setMaxLength(100)
        self.status_combo = QComboBox(self)
        self.status_combo.addItem("Đang sử dụng", "ACTIVE")
        self.status_combo.addItem("Ngừng sử dụng", "INACTIVE")
        for item in school_years:
            self.school_year_combo.addItem(
                item.year_name,
                item.school_year_id,
            )
        for item in grades:
            self.grade_combo.addItem(
                item.grade_name or f"Khối {item.grade_number}",
                item.grade_id,
            )
        form = QFormLayout()
        form.addRow("Tên lớp *", self.class_name_input)
        form.addRow("Năm học *", self.school_year_combo)
        form.addRow("Khối *", self.grade_combo)
        form.addRow("Giáo viên chủ nhiệm", self.teacher_input)
        form.addRow("Trạng thái", self.status_combo)
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        _build_dialog_shell(
            self, form, self.button_box, self.windowTitle(),
            "Gắn lớp với đúng năm học, khối và giáo viên chủ nhiệm.",
        )
        if school_class is not None:
            self.class_name_input.setText(school_class.class_name)
            self.teacher_input.setText(school_class.homeroom_teacher or "")
            self.school_year_combo.setCurrentIndex(
                self.school_year_combo.findData(school_class.school_year_id)
            )
            self.grade_combo.setCurrentIndex(
                self.grade_combo.findData(school_class.grade_id)
            )
            self.status_combo.setCurrentIndex(
                self.status_combo.findData(school_class.status)
            )

    def values(self) -> tuple[str, int, int, str | None, str]:
        return (
            self.class_name_input.text(),
            self.grade_combo.currentData(),
            self.school_year_combo.currentData(),
            self.teacher_input.text() or None,
            self.status_combo.currentData(),
        )


class SubjectDialog(QDialog):
    def __init__(
        self,
        subject: Subject | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Sửa môn học" if subject else "Thêm môn học")
        self.code_input = QLineEdit(self)
        self.code_input.setMaxLength(20)
        self.name_input = QLineEdit(self)
        self.name_input.setMaxLength(100)
        self.active_checkbox = QCheckBox("Đang sử dụng", self)
        self.active_checkbox.setChecked(True)
        form = QFormLayout()
        form.addRow("Mã môn *", self.code_input)
        form.addRow("Tên môn *", self.name_input)
        form.addRow("", self.active_checkbox)
        self.button_box = _dialog_buttons(self)
        _build_dialog_shell(
            self, form, self.button_box, self.windowTitle(),
            "Thông tin môn học được dùng xuyên suốt học vụ và báo cáo.",
        )
        if subject is not None:
            self.code_input.setText(subject.subject_code)
            self.name_input.setText(subject.subject_name)
            self.active_checkbox.setChecked(subject.is_active)

    def values(self) -> tuple[str, str, bool]:
        return (
            self.code_input.text(),
            self.name_input.text(),
            self.active_checkbox.isChecked(),
        )


class AssessmentDialog(QDialog):
    def __init__(
        self,
        school_years: list[SchoolYear],
        subjects: list[Subject],
        assessment: Assessment | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("assessmentDialog")
        self.setWindowTitle("Sửa bài đánh giá" if assessment else "Thêm bài đánh giá")
        self.resize(560, 600)
        self.title_label = QLabel(
            "Cập nhật bài đánh giá" if assessment else "Thêm bài đánh giá mới",
            self,
        )
        self.title_label.setProperty("dialogTitle", True)
        self.subtitle_label = QLabel(
            "Thiết lập đúng năm học, môn học và trạng thái sử dụng.",
            self,
        )
        self.subtitle_label.setProperty("dialogSubtitle", True)
        self.school_year_combo = QComboBox(self)
        self.subject_combo = QComboBox(self)
        self.name_input = QLineEdit(self)
        self.name_input.setMaxLength(150)
        self.semester_combo = QComboBox(self)
        self.semester_combo.addItem("Không xác định", None)
        self.semester_combo.addItem("Học kỳ 1", 1)
        self.semester_combo.addItem("Học kỳ 2", 2)
        self.type_input = QLineEdit(self)
        self.type_input.setMaxLength(30)
        self.has_date_checkbox = QCheckBox("Có ngày đánh giá", self)
        self.date_input = QDateEdit(QDate.currentDate(), self)
        self.date_input.setCalendarPopup(True)
        self.date_input.setDisplayFormat("dd/MM/yyyy")
        self.date_input.setEnabled(False)
        self.has_date_checkbox.toggled.connect(self.date_input.setEnabled)
        self.status_combo = QComboBox(self)
        for status, label in (
            (AssessmentStatus.ACTIVE, "Đang sử dụng"),
            (AssessmentStatus.LOCKED, "Đã khóa"),
            (AssessmentStatus.CANCELLED, "Ngừng sử dụng"),
        ):
            self.status_combo.addItem(label, status)
        for item in school_years:
            self.school_year_combo.addItem(item.year_name, item.school_year_id)
        for item in subjects:
            self.subject_combo.addItem(item.subject_name, item.subject_id)
        self.form_card = QFrame(self)
        self.form_card.setObjectName("dialogCard")
        self.form_card.setProperty("dialogCard", True)
        form = QFormLayout(self.form_card)
        form.setContentsMargins(20, 18, 20, 18)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(12)
        form.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow
        )
        form.addRow("Năm học *", self.school_year_combo)
        form.addRow("Môn học *", self.subject_combo)
        form.addRow("Tên bài *", self.name_input)
        form.addRow("Học kỳ", self.semester_combo)
        form.addRow("Loại bài", self.type_input)
        form.addRow("", self.has_date_checkbox)
        form.addRow("Ngày đánh giá", self.date_input)
        form.addRow("Trạng thái", self.status_combo)
        self.button_box = _dialog_buttons(self)
        self.save_button = self.button_box.button(
            QDialogButtonBox.StandardButton.Save
        )
        self.cancel_button = self.button_box.button(
            QDialogButtonBox.StandardButton.Cancel
        )
        self.save_button.setText("Lưu" if assessment else "Thêm bài")
        self.cancel_button.setText("Hủy")
        self.save_button.setObjectName("primaryDialogButton")
        self.save_button.setProperty("variant", "primary")
        self.cancel_button.setProperty("variant", "secondary")
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(14)
        root.addWidget(self.title_label)
        root.addWidget(self.subtitle_label)
        root.addWidget(self.form_card, 1)
        root.addWidget(self.button_box)
        if assessment is not None:
            self.school_year_combo.setCurrentIndex(
                self.school_year_combo.findData(assessment.school_year_id)
            )
            self.subject_combo.setCurrentIndex(
                self.subject_combo.findData(assessment.subject_id)
            )
            self.name_input.setText(assessment.assessment_name)
            self.semester_combo.setCurrentIndex(
                self.semester_combo.findData(assessment.semester)
            )
            self.type_input.setText(assessment.assessment_type or "")
            if assessment.assessment_date is not None:
                self.has_date_checkbox.setChecked(True)
                self.date_input.setDate(_qt_date(assessment.assessment_date))
            self.status_combo.setCurrentIndex(
                self.status_combo.findData(assessment.status)
            )
        self.setStyleSheet(dialog_stylesheet())

    def values(self):
        assessment_date = (
            _python_date(self.date_input.date())
            if self.has_date_checkbox.isChecked()
            else None
        )
        return (
            self.subject_combo.currentData(),
            self.school_year_combo.currentData(),
            self.name_input.text(),
            self.semester_combo.currentData(),
            self.type_input.text() or None,
            assessment_date,
            self.status_combo.currentData(),
        )


class SupportRuleDialog(QDialog):
    def __init__(
        self,
        school_years: list[SchoolYear],
        subjects: list[Subject],
        rule: SupportRule | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Sửa ngưỡng bổ trợ" if rule else "Thêm ngưỡng bổ trợ")
        self.school_year_combo = QComboBox(self)
        self.subject_combo = QComboBox(self)
        self.threshold_input = QLineEdit(self)
        self.active_checkbox = QCheckBox("Đang sử dụng", self)
        self.active_checkbox.setChecked(True)
        for item in school_years:
            self.school_year_combo.addItem(item.year_name, item.school_year_id)
        for item in subjects:
            self.subject_combo.addItem(item.subject_name, item.subject_id)
        form = QFormLayout()
        form.addRow("Năm học *", self.school_year_combo)
        form.addRow("Môn học *", self.subject_combo)
        form.addRow("Ngưỡng *", self.threshold_input)
        form.addRow("", self.active_checkbox)
        self.button_box = _dialog_buttons(self)
        explanation = QLabel(
            "Học sinh có điểm thấp hơn ngưỡng đang áp dụng sẽ được đưa vào luồng xem xét hỗ trợ.",
            self,
        )
        explanation.setWordWrap(True)
        form.addRow("", explanation)
        _build_dialog_shell(
            self, form, self.button_box, self.windowTitle(),
            "Cấu hình ngưỡng theo đúng năm học và môn học.",
        )
        if rule is not None:
            self.school_year_combo.setCurrentIndex(
                self.school_year_combo.findData(rule.school_year_id)
            )
            self.subject_combo.setCurrentIndex(
                self.subject_combo.findData(rule.subject_id)
            )
            self.threshold_input.setText(str(rule.threshold))
            self.active_checkbox.setChecked(rule.is_active)
            self.active_checkbox.setEnabled(False)
            self.school_year_combo.setEnabled(False)
            self.subject_combo.setEnabled(False)

    def values(self) -> tuple[int, int, str, bool]:
        return (
            self.subject_combo.currentData(),
            self.school_year_combo.currentData(),
            self.threshold_input.text(),
            self.active_checkbox.isChecked(),
        )


def _dialog_buttons(dialog: QDialog) -> QDialogButtonBox:
    buttons = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Save
        | QDialogButtonBox.StandardButton.Cancel,
        dialog,
    )
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    return buttons
