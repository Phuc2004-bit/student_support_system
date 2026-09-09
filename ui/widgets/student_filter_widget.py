from __future__ import annotations

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import QComboBox, QGridLayout, QLabel, QLineEdit, QWidget

from models.dto.student_filter import StudentFilter
from models.enums import StudentStatus


class StudentFilterWidget(QWidget):
    filters_changed = Signal(object)

    def __init__(self, academic_service=None, parent=None):
        super().__init__(parent)
        self.academic_service = academic_service
        self._grades = []
        self._classes = []

        self.setObjectName("studentFilterWidget")
        self._build_ui()
        self._connect_signals()
        self._load_statuses()

    def _build_ui(self) -> None:
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(6)

        self.search_input = QLineEdit(self)
        self.search_input.setObjectName("studentSearchInput")
        self.search_input.setPlaceholderText("Tìm theo mã học sinh, họ tên...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setMinimumWidth(260)

        self.school_year_combo = QComboBox(self)
        self.school_year_combo.setObjectName("studentSchoolYearCombo")
        self.grade_combo = QComboBox(self)
        self.grade_combo.setObjectName("studentGradeCombo")
        self.class_combo = QComboBox(self)
        self.class_combo.setObjectName("studentClassCombo")
        self.status_combo = QComboBox(self)
        self.status_combo.setObjectName("studentStatusCombo")

        controls = (
            ("Tìm kiếm", self.search_input),
            ("Năm học", self.school_year_combo),
            ("Khối", self.grade_combo),
            ("Lớp", self.class_combo),
            ("Trạng thái", self.status_combo),
        )
        for column, (text, control) in enumerate(controls):
            label = QLabel(text, self)
            label.setProperty("studentFilterLabel", True)
            label.setObjectName(f"studentFilterLabel_{column}")
            layout.addWidget(label, 0, column)
            layout.addWidget(control, 1, column)
            layout.setColumnStretch(column, 3 if column == 0 else 1)

    def _connect_signals(self) -> None:
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(300)
        self._timer.timeout.connect(self._emit)
        self.search_input.textChanged.connect(lambda _text: self._timer.start())
        self.school_year_combo.currentIndexChanged.connect(self._year_changed)
        self.grade_combo.currentIndexChanged.connect(self._grade_changed)
        self.class_combo.currentIndexChanged.connect(lambda _index: self._emit())
        self.status_combo.currentIndexChanged.connect(lambda _index: self._emit())

    def _load_statuses(self) -> None:
        self.status_combo.clear()
        self.status_combo.addItem("Tất cả trạng thái", None)
        self.status_combo.addItem("Đang học", StudentStatus.ACTIVE)
        self.status_combo.addItem("Ngừng hoạt động", StudentStatus.INACTIVE)

    def load_options(self) -> None:
        if self.academic_service is None:
            return

        years = self.academic_service.list_school_years()
        self.school_year_combo.blockSignals(True)
        self.school_year_combo.clear()
        self.school_year_combo.addItem("Tất cả năm học", None)
        current_index = 0
        for row in years:
            year_id, year_name, *rest = row
            self.school_year_combo.addItem(year_name, year_id)
            if rest and bool(rest[-1]):
                current_index = self.school_year_combo.count() - 1
        self.school_year_combo.setCurrentIndex(current_index)
        self.school_year_combo.blockSignals(False)

        self._grades = list(self.academic_service.list_grades())
        self.grade_combo.blockSignals(True)
        self.grade_combo.clear()
        self.grade_combo.addItem("Tất cả khối", None)
        for grade_id, grade_number, *_ in self._grades:
            self.grade_combo.addItem(f"Khối {grade_number}", grade_id)
        self.grade_combo.blockSignals(False)
        self._reload_classes()
        self._emit()

    def _year_changed(self, _index) -> None:
        self._reload_classes()
        self._emit()

    def _grade_changed(self, _index) -> None:
        self._reload_classes()
        self._emit()

    def _reload_classes(self) -> None:
        self.class_combo.blockSignals(True)
        self.class_combo.clear()
        self.class_combo.addItem("Tất cả lớp", None)
        if self.academic_service is not None:
            year_id = self.school_year_combo.currentData()
            if year_id is not None:
                grade_id = self.grade_combo.currentData()
                grade_number = None
                for candidate_id, candidate_number, *_ in self._grades:
                    if candidate_id == grade_id:
                        grade_number = candidate_number
                        break
                for row in self.academic_service.list_classes_by_school_year(year_id):
                    class_id, class_name, row_grade_number, *rest = row
                    is_active = True if not rest else bool(rest[-1])
                    if not is_active:
                        continue
                    if grade_number is not None and row_grade_number != grade_number:
                        continue
                    self.class_combo.addItem(class_name, class_id)
        self.class_combo.blockSignals(False)

    def current_value(self) -> StudentFilter:
        return StudentFilter(
            search_text=self.search_input.text(),
            school_year_id=self.school_year_combo.currentData(),
            grade_id=self.grade_combo.currentData(),
            class_id=self.class_combo.currentData(),
            status=self.status_combo.currentData(),
        )

    def _emit(self) -> None:
        self.filters_changed.emit(self.current_value())
