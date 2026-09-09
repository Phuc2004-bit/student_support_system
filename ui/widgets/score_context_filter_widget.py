from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QLabel,
    QWidget,
)

from models.enums import AssessmentStatus


@dataclass(frozen=True, slots=True)
class ScoreContextSelection:
    school_year_id: int | None = None
    grade_id: int | None = None
    class_id: int | None = None
    subject_id: int | None = None
    assessment_id: int | None = None

    @property
    def is_complete(self) -> bool:
        return all(
            value is not None
            for value in (
                self.school_year_id,
                self.grade_id,
                self.class_id,
                self.subject_id,
                self.assessment_id,
            )
        )


class ScoreContextFilterWidget(QWidget):
    context_changed = Signal(object)

    def __init__(self, academic_service=None, parent=None):
        super().__init__(parent)
        self.academic_service = academic_service
        self._grades: list[tuple] = []
        self._assessments_by_id: dict[int, object] = {}
        self.setObjectName("scoreContextFilterWidget")

        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(6)

        self.school_year_combo = QComboBox(self)
        self.grade_combo = QComboBox(self)
        self.class_combo = QComboBox(self)
        self.subject_combo = QComboBox(self)
        self.assessment_combo = QComboBox(self)

        controls = (
            ("Năm học", self.school_year_combo),
            ("Khối", self.grade_combo),
            ("Lớp", self.class_combo),
            ("Môn học", self.subject_combo),
            ("Bài đánh giá", self.assessment_combo),
        )
        for column, (label, combo) in enumerate(controls):
            label_widget = QLabel(label, self)
            label_widget.setProperty("scoreFilterLabel", True)
            combo.setObjectName(
                (
                    "schoolYearScoreCombo",
                    "gradeScoreCombo",
                    "classScoreCombo",
                    "subjectScoreCombo",
                    "assessmentScoreCombo",
                )[column]
            )
            combo.setMinimumWidth(145)
            grid.addWidget(label_widget, 0, column)
            grid.addWidget(combo, 1, column)
            grid.setColumnStretch(column, 1)

        self.school_year_combo.currentIndexChanged.connect(
            self._year_changed
        )
        self.grade_combo.currentIndexChanged.connect(
            self._grade_changed
        )
        self.class_combo.currentIndexChanged.connect(
            self._class_changed
        )
        self.subject_combo.currentIndexChanged.connect(
            self._subject_changed
        )
        self.assessment_combo.currentIndexChanged.connect(
            self._emit
        )

        self._reset_all()

    def load_options(self) -> None:
        self._reset_all()
        if self.academic_service is None:
            self._emit()
            return

        years = self.academic_service.list_school_years()
        current_index = 0

        self.school_year_combo.blockSignals(True)
        for row in years:
            year_id, year_name, *rest = row
            self.school_year_combo.addItem(str(year_name), year_id)
            if rest and bool(rest[-1]):
                current_index = self.school_year_combo.count() - 1
        self.school_year_combo.setCurrentIndex(current_index)
        self.school_year_combo.blockSignals(False)

        self._year_changed(self.school_year_combo.currentIndex())

    def current_value(self) -> ScoreContextSelection:
        return ScoreContextSelection(
            school_year_id=self.school_year_combo.currentData(),
            grade_id=self.grade_combo.currentData(),
            class_id=self.class_combo.currentData(),
            subject_id=self.subject_combo.currentData(),
            assessment_id=self.assessment_combo.currentData(),
        )

    def selected_assessment(self):
        """Return already-loaded assessment metadata for presentation only."""

        return self._assessments_by_id.get(
            self.assessment_combo.currentData()
        )

    def _reset_all(self) -> None:
        self._grades = []
        self._assessments_by_id = {}
        self._reset_combo(
            self.school_year_combo,
            "Chọn năm học",
            enabled=self.academic_service is not None,
        )
        self._reset_combo(self.grade_combo, "Chọn khối")
        self._reset_combo(self.class_combo, "Chọn lớp")
        self._reset_combo(self.subject_combo, "Chọn môn học")
        self._reset_combo(
            self.assessment_combo,
            "Chọn bài đánh giá",
        )

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
        self._reload_grades()
        self._reload_classes()
        self._reload_subjects()
        self._reload_assessments()
        self._emit()

    def _grade_changed(self, _index: int) -> None:
        self._reload_classes()
        self._reload_subjects()
        self._reload_assessments()
        self._emit()

    def _class_changed(self, _index: int) -> None:
        self._reload_subjects()
        self._reload_assessments()
        self._emit()

    def _subject_changed(self, _index: int) -> None:
        self._reload_assessments()
        self._emit()

    def _reload_grades(self) -> None:
        year_id = self.school_year_combo.currentData()
        self._reset_combo(
            self.grade_combo,
            "Chọn khối",
            enabled=year_id is not None,
        )
        self._grades = []
        if year_id is None or self.academic_service is None:
            return

        self._grades = list(self.academic_service.list_grades())
        self.grade_combo.blockSignals(True)
        for grade_id, grade_number, *_ in self._grades:
            self.grade_combo.addItem(
                f"Khối {grade_number}",
                grade_id,
            )
        self.grade_combo.blockSignals(False)

    def _reload_classes(self) -> None:
        year_id = self.school_year_combo.currentData()
        grade_id = self.grade_combo.currentData()
        enabled = year_id is not None and grade_id is not None
        self._reset_combo(
            self.class_combo,
            "Chọn lớp",
            enabled=enabled,
        )
        if not enabled or self.academic_service is None:
            return

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
        for class_id, class_name, row_grade_number, *_ in classes:
            if row_grade_number == grade_number:
                self.class_combo.addItem(str(class_name), class_id)
        self.class_combo.blockSignals(False)

    def _reload_subjects(self) -> None:
        class_id = self.class_combo.currentData()
        self._reset_combo(
            self.subject_combo,
            "Chọn môn học",
            enabled=class_id is not None,
        )
        if class_id is None or self.academic_service is None:
            return

        subjects = self.academic_service.list_active_subjects()
        self.subject_combo.blockSignals(True)
        for subject_id, _subject_code, subject_name, *_ in subjects:
            self.subject_combo.addItem(
                str(subject_name),
                subject_id,
            )
        self.subject_combo.blockSignals(False)

    def _reload_assessments(self) -> None:
        self._assessments_by_id = {}
        value = self.current_value()
        enabled = (
            value.school_year_id is not None
            and value.class_id is not None
            and value.subject_id is not None
        )
        self._reset_combo(
            self.assessment_combo,
            "Chọn bài đánh giá",
            enabled=enabled,
        )
        if not enabled or self.academic_service is None:
            return

        active_reader = getattr(
            self.academic_service,
            "list_active_assessments",
            None,
        )
        if active_reader is not None:
            assessments = active_reader(
                value.school_year_id,
                subject_id=value.subject_id,
            )
        else:
            assessments = [
                item
                for item in self.academic_service.list_assessments(
                    value.school_year_id,
                    subject_id=value.subject_id,
                )
                if item.status == AssessmentStatus.ACTIVE
            ]
        self.assessment_combo.blockSignals(True)
        for assessment in assessments:
            self._assessments_by_id[assessment.assessment_id] = assessment
            self.assessment_combo.addItem(
                assessment.assessment_name,
                assessment.assessment_id,
            )
        self.assessment_combo.blockSignals(False)

    def _emit(self, *_args) -> None:
        self.context_changed.emit(self.current_value())
