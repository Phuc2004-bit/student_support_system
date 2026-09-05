from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from models.dto import Grade, SchoolClass, SchoolYear


def _python_date(value: QDate) -> date:
    return date(value.year(), value.month(), value.day())


def _qt_date(value: date) -> QDate:
    return QDate(value.year, value.month, value.day)


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
        root = QVBoxLayout(self)
        root.addLayout(form)
        root.addWidget(self.button_box)
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
        root = QVBoxLayout(self)
        root.addLayout(form)
        root.addWidget(self.button_box)
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
        root = QVBoxLayout(self)
        root.addLayout(form)
        root.addWidget(self.button_box)
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
