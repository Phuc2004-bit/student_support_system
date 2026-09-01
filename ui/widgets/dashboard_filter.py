from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QLabel,
    QWidget,
)

from services.academic_service import AcademicService


@dataclass(frozen=True)
class DashboardFilterValue:
    school_year_id: int | None
    grade_id: int | None
    class_id: int | None
    subject_id: int | None


class DashboardFilterWidget(QWidget):
    """
    Bộ lọc Dashboard.

    Quan hệ:
    - Năm học là bắt buộc khi có dữ liệu.
    - Khối/Lớp/Môn cho phép "Tất cả".
    - Đổi năm học -> nạp lại lớp.
    - Đổi khối -> lọc danh sách lớp đã nạp của năm học.
    """

    filters_changed = Signal(object)

    def __init__(
        self,
        academic_service: AcademicService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        if academic_service is None:
            raise ValueError(
                "AcademicService không được để trống."
            )

        self.academic_service = academic_service
        self._grades: list[tuple] = []
        self._classes: list[tuple] = []
        self._subjects: list[tuple] = []
        self._loading = False

        self.setObjectName("dashboardFilterWidget")
        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(6)

        self.school_year_combo = QComboBox(self)
        self.school_year_combo.setObjectName(
            "dashboardSchoolYearCombo"
        )

        self.grade_combo = QComboBox(self)
        self.grade_combo.setObjectName(
            "dashboardGradeCombo"
        )

        self.class_combo = QComboBox(self)
        self.class_combo.setObjectName(
            "dashboardClassCombo"
        )

        self.subject_combo = QComboBox(self)
        self.subject_combo.setObjectName(
            "dashboardSubjectCombo"
        )

        controls = (
            ("Năm học", self.school_year_combo),
            ("Khối", self.grade_combo),
            ("Lớp", self.class_combo),
            ("Môn", self.subject_combo),
        )

        for column, (text, combo) in enumerate(controls):
            label = QLabel(text, self)
            label.setObjectName(
                f"dashboardFilterLabel_{column}"
            )
            layout.addWidget(label, 0, column)
            layout.addWidget(combo, 1, column)
            layout.setColumnStretch(column, 1)

    def _connect_signals(self) -> None:
        self.school_year_combo.currentIndexChanged.connect(
            self._on_school_year_changed
        )
        self.grade_combo.currentIndexChanged.connect(
            self._on_grade_changed
        )
        self.class_combo.currentIndexChanged.connect(
            self._emit_filters_changed
        )
        self.subject_combo.currentIndexChanged.connect(
            self._emit_filters_changed
        )

    def load_options(self) -> None:
        self._loading = True
        try:
            school_years = self.academic_service.list_school_years()
            self._grades = self.academic_service.list_grades()
            self._subjects = self.academic_service.list_active_subjects()

            self._fill_school_years(school_years)
            self._fill_grades()
            self._fill_subjects()
            self._load_classes_for_selected_year()
        finally:
            self._loading = False

        self.filters_changed.emit(self.current_value())

    def current_value(self) -> DashboardFilterValue:
        return DashboardFilterValue(
            school_year_id=self.school_year_combo.currentData(),
            grade_id=self.grade_combo.currentData(),
            class_id=self.class_combo.currentData(),
            subject_id=self.subject_combo.currentData(),
        )

    def _fill_school_years(self, school_years: list[tuple]) -> None:
        self.school_year_combo.clear()

        current_index = -1
        for index, item in enumerate(school_years):
            school_year_id, year_name, _, _, is_current = item
            self.school_year_combo.addItem(
                str(year_name),
                int(school_year_id),
            )
            if is_current:
                current_index = index

        if current_index >= 0:
            self.school_year_combo.setCurrentIndex(current_index)

    def _fill_grades(self) -> None:
        self.grade_combo.clear()
        self.grade_combo.addItem("Tất cả khối", None)

        for grade_id, grade_number, _ in self._grades:
            self.grade_combo.addItem(
                f"Khối {grade_number}",
                int(grade_id),
            )

    def _fill_subjects(self) -> None:
        self.subject_combo.clear()
        self.subject_combo.addItem("Tất cả môn", None)

        for subject_id, _, subject_name in self._subjects:
            self.subject_combo.addItem(
                str(subject_name),
                int(subject_id),
            )

    def _load_classes_for_selected_year(self) -> None:
        school_year_id = self.school_year_combo.currentData()

        if school_year_id is None:
            self._classes = []
        else:
            self._classes = (
                self.academic_service.list_classes_by_school_year(
                    int(school_year_id)
                )
            )

        self._rebuild_class_combo()

    def _rebuild_class_combo(self) -> None:
        selected_class_id = self.class_combo.currentData()
        selected_grade_number = self._selected_grade_number()

        self.class_combo.blockSignals(True)
        try:
            self.class_combo.clear()
            self.class_combo.addItem("Tất cả lớp", None)

            restored_index = 0

            for class_id, class_name, grade_number, _, status in self._classes:
                if str(status).upper() != "ACTIVE":
                    continue

                if (
                    selected_grade_number is not None
                    and int(grade_number) != selected_grade_number
                ):
                    continue

                self.class_combo.addItem(
                    str(class_name),
                    int(class_id),
                )

                if selected_class_id == class_id:
                    restored_index = self.class_combo.count() - 1

            self.class_combo.setCurrentIndex(restored_index)
        finally:
            self.class_combo.blockSignals(False)

    def _selected_grade_number(self) -> int | None:
        grade_id = self.grade_combo.currentData()

        if grade_id is None:
            return None

        for item_grade_id, grade_number, _ in self._grades:
            if int(item_grade_id) == int(grade_id):
                return int(grade_number)

        return None

    def _on_school_year_changed(self) -> None:
        if self._loading:
            return

        self._load_classes_for_selected_year()
        self._emit_filters_changed()

    def _on_grade_changed(self) -> None:
        if self._loading:
            return

        self._rebuild_class_combo()
        self._emit_filters_changed()

    def _emit_filters_changed(self) -> None:
        if not self._loading:
            self.filters_changed.emit(
                self.current_value()
            )
