from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QLabel,
    QWidget,
)

from models.enums import InterventionStatus
from models.dto.report_export import SupportReportExportContext
from ui.widgets.dashboard_charts import status_label


@dataclass(frozen=True, slots=True)
class SupportFilterSelection:
    school_year_id: int | None = None
    grade_id: int | None = None
    class_id: int | None = None
    subject_id: int | None = None
    status: InterventionStatus | None = None


class SupportFilterWidget(QWidget):
    filters_changed = Signal(object)

    def __init__(self, academic_service=None, parent=None):
        super().__init__(parent)
        self.setObjectName("supportFilterWidget")
        self.academic_service = academic_service
        self._grades: list[tuple] = []

        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(6)

        self.school_year_combo = QComboBox(self)
        self.grade_combo = QComboBox(self)
        self.class_combo = QComboBox(self)
        self.subject_combo = QComboBox(self)
        self.status_combo = QComboBox(self)

        controls = (
            ("Năm học", self.school_year_combo),
            ("Khối", self.grade_combo),
            ("Lớp", self.class_combo),
            ("Môn học", self.subject_combo),
            ("Trạng thái", self.status_combo),
        )
        for column, (text, combo) in enumerate(controls):
            label = QLabel(text, self)
            label.setProperty("supportFilterLabel", True)
            combo.setObjectName(
                (
                    "supportSchoolYearFilter",
                    "supportGradeFilter",
                    "supportClassFilter",
                    "supportSubjectFilter",
                    "supportStatusFilter",
                )[column]
            )
            combo.setMinimumWidth(132)
            grid.addWidget(label, 0, column)
            grid.addWidget(combo, 1, column)
            grid.setColumnStretch(column, 1)

        self.school_year_combo.currentIndexChanged.connect(
            self._year_changed
        )
        self.grade_combo.currentIndexChanged.connect(
            self._grade_changed
        )
        self.class_combo.currentIndexChanged.connect(self._emit)
        self.subject_combo.currentIndexChanged.connect(self._emit)
        self.status_combo.currentIndexChanged.connect(self._emit)

        self._reset_options()
        self._load_statuses()

    def load_options(self) -> None:
        self._reset_options()
        self._load_statuses()

        if self.academic_service is None:
            self._emit()
            return

        years = self.academic_service.list_school_years()
        self._grades = list(self.academic_service.list_grades())
        subjects = self.academic_service.list_active_subjects()

        current_index = 0
        self.school_year_combo.blockSignals(True)
        for year_id, year_name, *rest in years:
            self.school_year_combo.addItem(str(year_name), year_id)
            if rest and bool(rest[-1]):
                current_index = self.school_year_combo.count() - 1
        self.school_year_combo.setCurrentIndex(current_index)
        self.school_year_combo.blockSignals(False)

        self.grade_combo.blockSignals(True)
        for grade_id, grade_number, *_ in self._grades:
            self.grade_combo.addItem(f"Khối {grade_number}", grade_id)
        self.grade_combo.setEnabled(
            bool(self._grades)
            and self.school_year_combo.currentData() is not None
        )
        self.grade_combo.blockSignals(False)

        self.subject_combo.blockSignals(True)
        for subject_id, _subject_code, subject_name, *_ in subjects:
            self.subject_combo.addItem(str(subject_name), subject_id)
        self.subject_combo.setEnabled(bool(subjects))
        self.subject_combo.blockSignals(False)

        self._reload_classes()
        self._emit()

    def current_value(self) -> SupportFilterSelection:
        return SupportFilterSelection(
            school_year_id=self.school_year_combo.currentData(),
            grade_id=self.grade_combo.currentData(),
            class_id=self.class_combo.currentData(),
            subject_id=self.subject_combo.currentData(),
            status=self.status_combo.currentData(),
        )

    def export_context(self) -> SupportReportExportContext | None:
        selection = self.current_value()
        if selection.school_year_id is None:
            return None
        return SupportReportExportContext(
            school_year_id=selection.school_year_id,
            school_year_name=self.school_year_combo.currentText(),
            grade_id=selection.grade_id,
            grade_name=(
                self.grade_combo.currentText()
                if selection.grade_id is not None
                else None
            ),
            class_id=selection.class_id,
            class_name=(
                self.class_combo.currentText()
                if selection.class_id is not None
                else None
            ),
            subject_id=selection.subject_id,
            subject_name=(
                self.subject_combo.currentText()
                if selection.subject_id is not None
                else None
            ),
            status=selection.status,
        )

    def _reset_options(self) -> None:
        self._grades = []
        enabled = self.academic_service is not None
        self._reset_combo(
            self.school_year_combo,
            "Chọn năm học",
            enabled=enabled,
        )
        self._reset_combo(self.grade_combo, "Tất cả khối")
        self._reset_combo(self.class_combo, "Tất cả lớp")
        self._reset_combo(self.subject_combo, "Tất cả môn")

    def _load_statuses(self) -> None:
        self.status_combo.blockSignals(True)
        self.status_combo.clear()
        self.status_combo.addItem("Tất cả trạng thái", None)
        for status in InterventionStatus:
            self.status_combo.addItem(status_label(status.value), status)
        self.status_combo.setEnabled(True)
        self.status_combo.blockSignals(False)

    @staticmethod
    def _reset_combo(
        combo: QComboBox,
        placeholder: str,
        enabled: bool = False,
    ) -> None:
        combo.blockSignals(True)
        combo.clear()
        combo.addItem(placeholder, None)
        combo.setCurrentIndex(0)
        combo.setEnabled(enabled)
        combo.blockSignals(False)

    def _year_changed(self, _index: int) -> None:
        self.grade_combo.setEnabled(
            bool(self._grades)
            and self.school_year_combo.currentData() is not None
        )
        self.grade_combo.blockSignals(True)
        self.grade_combo.setCurrentIndex(0)
        self.grade_combo.blockSignals(False)
        self._reload_classes()
        self._emit()

    def _grade_changed(self, _index: int) -> None:
        self._reload_classes()
        self._emit()

    def _reload_classes(self) -> None:
        year_id = self.school_year_combo.currentData()
        self._reset_combo(
            self.class_combo,
            "Tất cả lớp",
            enabled=year_id is not None,
        )
        if year_id is None or self.academic_service is None:
            return

        grade_id = self.grade_combo.currentData()
        grade_number = next(
            (
                number
                for item_id, number, *_ in self._grades
                if item_id == grade_id
            ),
            None,
        )
        classes = self.academic_service.list_classes_by_school_year(
            year_id
        )

        self.class_combo.blockSignals(True)
        for class_id, class_name, row_grade_number, *rest in classes:
            is_active = True if not rest else bool(rest[-1])
            if not is_active:
                continue
            if (
                grade_number is not None
                and row_grade_number != grade_number
            ):
                continue
            self.class_combo.addItem(str(class_name), class_id)
        self.class_combo.blockSignals(False)

    def _emit(self, *_args) -> None:
        self.filters_changed.emit(self.current_value())
