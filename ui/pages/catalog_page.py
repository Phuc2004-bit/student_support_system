from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from exceptions import AppError
from models.dto import (
    Assessment,
    Grade,
    SchoolClass,
    SchoolYear,
    Subject,
    SupportRule,
)
from models.enums import AssessmentStatus
from services.catalog_contract import CatalogServiceContract
from ui.dialogs.catalog_dialogs import (
    AssessmentDialog,
    ClassDialog,
    GradeDialog,
    SchoolYearDialog,
    SubjectDialog,
    SupportRuleDialog,
)


class CatalogPage(QWidget):
    def __init__(
        self,
        academic_service: CatalogServiceContract | None = None,
        school_year_dialog_factory=SchoolYearDialog,
        grade_dialog_factory=GradeDialog,
        class_dialog_factory=ClassDialog,
        subject_dialog_factory=SubjectDialog,
        assessment_dialog_factory=AssessmentDialog,
        support_rule_dialog_factory=SupportRuleDialog,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.academic_service = academic_service
        self.school_year_dialog_factory = school_year_dialog_factory
        self.grade_dialog_factory = grade_dialog_factory
        self.class_dialog_factory = class_dialog_factory
        self.subject_dialog_factory = subject_dialog_factory
        self.assessment_dialog_factory = assessment_dialog_factory
        self.support_rule_dialog_factory = support_rule_dialog_factory
        self.school_years: tuple[SchoolYear, ...] = ()
        self.grades: tuple[Grade, ...] = ()
        self.classes: tuple[SchoolClass, ...] = ()
        self.subjects: tuple[Subject, ...] = ()
        self.assessments: tuple[Assessment, ...] = ()
        self.support_rules: tuple[SupportRule, ...] = ()
        self.setObjectName("catalogPage")
        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 24)
        root.setSpacing(16)
        self.title_label = QLabel("Danh mục", self)
        self.subtitle_label = QLabel(
            "Quản lý năm học, khối và lớp học.",
            self,
        )
        self.state_label = QLabel(self)
        self.state_label.setWordWrap(True)
        root.addWidget(self.title_label)
        root.addWidget(self.subtitle_label)
        root.addWidget(self.state_label)

        self.tabs = QTabWidget(self)
        self.school_year_tab = QWidget(self.tabs)
        self.grade_tab = QWidget(self.tabs)
        self.class_tab = QWidget(self.tabs)
        self.tabs.addTab(self.school_year_tab, "Năm học")
        self.tabs.addTab(self.grade_tab, "Khối")
        self.tabs.addTab(self.class_tab, "Lớp")
        root.addWidget(self.tabs, 1)
        self._build_school_year_tab()
        self._build_grade_tab()
        self._build_class_tab()
        self.advanced_tabs = QTabWidget(self)
        self.subject_tab = QWidget(self.advanced_tabs)
        self.assessment_tab = QWidget(self.advanced_tabs)
        self.support_rule_tab = QWidget(self.advanced_tabs)
        self.advanced_tabs.addTab(self.subject_tab, "Môn học")
        self.advanced_tabs.addTab(self.assessment_tab, "Bài đánh giá")
        self.advanced_tabs.addTab(self.support_rule_tab, "Ngưỡng bổ trợ")
        root.addWidget(self.advanced_tabs, 1)
        self._build_subject_tab()
        self._build_assessment_tab()
        self._build_support_rule_tab()

    def _build_school_year_tab(self) -> None:
        layout = QVBoxLayout(self.school_year_tab)
        actions = QHBoxLayout()
        self.add_school_year_button = QPushButton("Thêm năm học", self)
        self.edit_school_year_button = QPushButton("Sửa", self)
        self.refresh_school_year_button = QPushButton("Làm mới", self)
        actions.addWidget(self.add_school_year_button)
        actions.addWidget(self.edit_school_year_button)
        actions.addStretch(1)
        actions.addWidget(self.refresh_school_year_button)
        layout.addLayout(actions)
        self.school_year_table = self._make_table(
            ("Tên năm học", "Ngày bắt đầu", "Ngày kết thúc", "Hiện tại"),
            0,
        )
        layout.addWidget(self.school_year_table, 1)

    def _build_grade_tab(self) -> None:
        layout = QVBoxLayout(self.grade_tab)
        actions = QHBoxLayout()
        self.add_grade_button = QPushButton("Thêm khối", self)
        self.edit_grade_button = QPushButton("Sửa tên", self)
        self.refresh_grade_button = QPushButton("Làm mới", self)
        actions.addWidget(self.add_grade_button)
        actions.addWidget(self.edit_grade_button)
        actions.addStretch(1)
        actions.addWidget(self.refresh_grade_button)
        layout.addLayout(actions)
        self.grade_table = self._make_table(("Số khối", "Tên hiển thị"), 1)
        layout.addWidget(self.grade_table, 1)

    def _build_class_tab(self) -> None:
        layout = QVBoxLayout(self.class_tab)
        filters = QHBoxLayout()
        self.class_year_combo = QComboBox(self.class_tab)
        self.class_grade_combo = QComboBox(self.class_tab)
        for label, control in (
            ("Năm học", self.class_year_combo),
            ("Khối", self.class_grade_combo),
        ):
            form = QFormLayout()
            form.addRow(label, control)
            filters.addLayout(form, 1)
        layout.addLayout(filters)
        actions = QHBoxLayout()
        self.add_class_button = QPushButton("Thêm lớp", self)
        self.edit_class_button = QPushButton("Sửa", self)
        self.toggle_class_button = QPushButton("Ngừng/Kích hoạt", self)
        self.refresh_class_button = QPushButton("Làm mới", self)
        actions.addWidget(self.add_class_button)
        actions.addWidget(self.edit_class_button)
        actions.addWidget(self.toggle_class_button)
        actions.addStretch(1)
        actions.addWidget(self.refresh_class_button)
        layout.addLayout(actions)
        self.class_table = self._make_table(
            ("Tên lớp", "Khối", "Năm học", "GVCN", "Trạng thái"),
            0,
        )
        layout.addWidget(self.class_table, 1)

    def _build_subject_tab(self) -> None:
        layout = QVBoxLayout(self.subject_tab)
        actions = QHBoxLayout()
        self.add_subject_button = QPushButton("Thêm môn", self)
        self.edit_subject_button = QPushButton("Sửa", self)
        self.toggle_subject_button = QPushButton("Ngừng/Kích hoạt", self)
        self.refresh_subject_button = QPushButton("Làm mới", self)
        actions.addWidget(self.add_subject_button)
        actions.addWidget(self.edit_subject_button)
        actions.addWidget(self.toggle_subject_button)
        actions.addStretch(1)
        actions.addWidget(self.refresh_subject_button)
        layout.addLayout(actions)
        self.subject_table = self._make_table(
            ("Mã môn", "Tên môn", "Trạng thái"),
            1,
        )
        layout.addWidget(self.subject_table, 1)

    def _build_assessment_tab(self) -> None:
        layout = QVBoxLayout(self.assessment_tab)
        filters = QHBoxLayout()
        self.assessment_year_combo = QComboBox(self.assessment_tab)
        self.assessment_subject_combo = QComboBox(self.assessment_tab)
        for label, control in (
            ("Năm học", self.assessment_year_combo),
            ("Môn học", self.assessment_subject_combo),
        ):
            form = QFormLayout()
            form.addRow(label, control)
            filters.addLayout(form, 1)
        layout.addLayout(filters)
        actions = QHBoxLayout()
        self.add_assessment_button = QPushButton("Thêm bài", self)
        self.edit_assessment_button = QPushButton("Sửa", self)
        self.toggle_assessment_button = QPushButton("Ngừng/Kích hoạt", self)
        self.refresh_assessment_button = QPushButton("Làm mới", self)
        actions.addWidget(self.add_assessment_button)
        actions.addWidget(self.edit_assessment_button)
        actions.addWidget(self.toggle_assessment_button)
        actions.addStretch(1)
        actions.addWidget(self.refresh_assessment_button)
        layout.addLayout(actions)
        self.assessment_table = self._make_table(
            ("Tên bài", "Năm học", "Môn học", "Học kỳ", "Loại", "Ngày", "Trạng thái"),
            0,
        )
        layout.addWidget(self.assessment_table, 1)

    def _build_support_rule_tab(self) -> None:
        layout = QVBoxLayout(self.support_rule_tab)
        filters = QHBoxLayout()
        self.rule_year_combo = QComboBox(self.support_rule_tab)
        self.rule_subject_combo = QComboBox(self.support_rule_tab)
        for label, control in (
            ("Năm học", self.rule_year_combo),
            ("Môn học", self.rule_subject_combo),
        ):
            form = QFormLayout()
            form.addRow(label, control)
            filters.addLayout(form, 1)
        layout.addLayout(filters)
        actions = QHBoxLayout()
        self.add_rule_button = QPushButton("Thêm ngưỡng", self)
        self.edit_rule_button = QPushButton("Sửa ngưỡng", self)
        self.toggle_rule_button = QPushButton("Ngừng/Kích hoạt", self)
        self.refresh_rule_button = QPushButton("Làm mới", self)
        actions.addWidget(self.add_rule_button)
        actions.addWidget(self.edit_rule_button)
        actions.addWidget(self.toggle_rule_button)
        actions.addStretch(1)
        actions.addWidget(self.refresh_rule_button)
        layout.addLayout(actions)
        self.rule_table = self._make_table(
            ("Năm học", "Môn học", "Ngưỡng", "Trạng thái"),
            1,
        )
        layout.addWidget(self.rule_table, 1)

    @staticmethod
    def _make_table(headers: tuple[str, ...], stretch_column: int) -> QTableWidget:
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        table.horizontalHeader().setSectionResizeMode(
            stretch_column,
            QHeaderView.ResizeMode.Stretch,
        )
        return table

    def _connect_signals(self) -> None:
        self.add_school_year_button.clicked.connect(self.create_school_year)
        self.edit_school_year_button.clicked.connect(self.edit_school_year)
        self.refresh_school_year_button.clicked.connect(self.initialize_catalogs)
        self.add_grade_button.clicked.connect(self.create_grade)
        self.edit_grade_button.clicked.connect(self.edit_grade)
        self.refresh_grade_button.clicked.connect(self.initialize_catalogs)
        self.add_class_button.clicked.connect(self.create_class)
        self.edit_class_button.clicked.connect(self.edit_class)
        self.toggle_class_button.clicked.connect(self.toggle_class_active)
        self.refresh_class_button.clicked.connect(self.refresh_classes)
        self.class_year_combo.currentIndexChanged.connect(self.refresh_classes)
        self.class_grade_combo.currentIndexChanged.connect(self.refresh_classes)
        self.add_subject_button.clicked.connect(self.create_subject)
        self.edit_subject_button.clicked.connect(self.edit_subject)
        self.toggle_subject_button.clicked.connect(self.toggle_subject_active)
        self.refresh_subject_button.clicked.connect(self.initialize_catalogs)
        self.add_assessment_button.clicked.connect(self.create_assessment)
        self.edit_assessment_button.clicked.connect(self.edit_assessment)
        self.toggle_assessment_button.clicked.connect(self.toggle_assessment_active)
        self.refresh_assessment_button.clicked.connect(self.refresh_assessments)
        self.assessment_year_combo.currentIndexChanged.connect(
            self.refresh_assessments
        )
        self.assessment_subject_combo.currentIndexChanged.connect(
            self.refresh_assessments
        )
        self.add_rule_button.clicked.connect(self.create_support_rule)
        self.edit_rule_button.clicked.connect(self.edit_support_rule)
        self.toggle_rule_button.clicked.connect(self.toggle_support_rule_active)
        self.refresh_rule_button.clicked.connect(self.refresh_support_rules)
        self.rule_year_combo.currentIndexChanged.connect(
            self.refresh_support_rules
        )
        self.rule_subject_combo.currentIndexChanged.connect(
            self.refresh_support_rules
        )

    def initialize_catalogs(self, *_args) -> bool:
        if self.academic_service is None:
            self._show_error("Chưa có dịch vụ quản lý danh mục.")
            return False
        try:
            self.school_years = tuple(
                self.academic_service.list_catalog_school_years()
            )
            self.grades = tuple(self.academic_service.list_catalog_grades())
            self._render_school_years()
            self._render_grades()
            self._load_class_filters()
            self.refresh_classes()
            if hasattr(self.academic_service, "list_catalog_subjects"):
                self.subjects = tuple(
                    self.academic_service.list_catalog_subjects()
                )
                self._render_subjects()
                self._load_advanced_filters()
                self.refresh_assessments()
                self.refresh_support_rules()
        except Exception:
            self._show_error()
            return False
        self.state_label.setText("Dữ liệu danh mục đã sẵn sàng.")
        return True

    def refresh_classes(self, *_args) -> bool:
        year_id = self.class_year_combo.currentData()
        if self.academic_service is None or year_id is None:
            self.classes = ()
            self._render_classes()
            return False
        try:
            self.classes = tuple(
                self.academic_service.list_catalog_classes(
                    school_year_id=year_id,
                    grade_id=self.class_grade_combo.currentData(),
                )
            )
            self._render_classes()
        except Exception:
            self.classes = ()
            self._render_classes()
            self._show_error()
            return False
        return True

    def refresh_assessments(self, *_args) -> bool:
        year_id = self.assessment_year_combo.currentData()
        if (
            self.academic_service is None
            or year_id is None
            or not hasattr(self.academic_service, "list_assessments")
        ):
            self.assessments = ()
            self._render_assessments()
            return False
        try:
            self.assessments = tuple(
                self.academic_service.list_assessments(
                    year_id,
                    subject_id=self.assessment_subject_combo.currentData(),
                )
            )
            self._render_assessments()
        except Exception:
            self.assessments = ()
            self._render_assessments()
            self._show_error()
            return False
        return True

    def refresh_support_rules(self, *_args) -> bool:
        year_id = self.rule_year_combo.currentData()
        if (
            self.academic_service is None
            or year_id is None
            or not hasattr(self.academic_service, "list_catalog_support_rules")
        ):
            self.support_rules = ()
            self._render_support_rules()
            return False
        try:
            self.support_rules = tuple(
                self.academic_service.list_catalog_support_rules(
                    year_id,
                    subject_id=self.rule_subject_combo.currentData(),
                )
            )
            self._render_support_rules()
        except Exception:
            self.support_rules = ()
            self._render_support_rules()
            self._show_error()
            return False
        return True

    def _render_school_years(self) -> None:
        self.school_year_table.setRowCount(len(self.school_years))
        for index, item in enumerate(self.school_years):
            values = (
                item.year_name,
                item.start_date.strftime("%d/%m/%Y") if item.start_date else "-",
                item.end_date.strftime("%d/%m/%Y") if item.end_date else "-",
                "Có" if item.is_current else "Không",
            )
            self._set_row(self.school_year_table, index, values, item.school_year_id)

    def _render_grades(self) -> None:
        self.grade_table.setRowCount(len(self.grades))
        for index, item in enumerate(self.grades):
            self._set_row(
                self.grade_table,
                index,
                (str(item.grade_number), item.grade_name or f"Khối {item.grade_number}"),
                item.grade_id,
            )

    def _render_classes(self) -> None:
        self.class_table.setRowCount(len(self.classes))
        for index, item in enumerate(self.classes):
            self._set_row(
                self.class_table,
                index,
                (
                    item.class_name,
                    str(item.grade_number),
                    item.school_year_name,
                    item.homeroom_teacher or "-",
                    "Đang sử dụng" if item.is_active else "Ngừng sử dụng",
                ),
                item.class_id,
            )

    def _render_subjects(self) -> None:
        self.subject_table.setRowCount(len(self.subjects))
        for index, item in enumerate(self.subjects):
            self._set_row(
                self.subject_table,
                index,
                (
                    item.subject_code,
                    item.subject_name,
                    "Đang sử dụng" if item.is_active else "Ngừng sử dụng",
                ),
                item.subject_id,
            )

    def _render_assessments(self) -> None:
        years = {item.school_year_id: item.year_name for item in self.school_years}
        subjects = {item.subject_id: item.subject_name for item in self.subjects}
        labels = {
            AssessmentStatus.ACTIVE: "Đang sử dụng",
            AssessmentStatus.LOCKED: "Đã khóa",
            AssessmentStatus.CANCELLED: "Ngừng sử dụng",
        }
        self.assessment_table.setRowCount(len(self.assessments))
        for index, item in enumerate(self.assessments):
            self._set_row(
                self.assessment_table,
                index,
                (
                    item.assessment_name,
                    years.get(item.school_year_id, "-"),
                    subjects.get(item.subject_id, "-"),
                    str(item.semester) if item.semester is not None else "-",
                    item.assessment_type or "-",
                    item.assessment_date.strftime("%d/%m/%Y")
                    if item.assessment_date
                    else "-",
                    labels.get(item.status, item.status.value),
                ),
                item.assessment_id,
            )

    def _render_support_rules(self) -> None:
        years = {item.school_year_id: item.year_name for item in self.school_years}
        subjects = {item.subject_id: item.subject_name for item in self.subjects}
        self.rule_table.setRowCount(len(self.support_rules))
        for index, item in enumerate(self.support_rules):
            self._set_row(
                self.rule_table,
                index,
                (
                    years.get(item.school_year_id, "-"),
                    subjects.get(item.subject_id, "-"),
                    str(item.threshold),
                    "Đang sử dụng" if item.is_active else "Ngừng sử dụng",
                ),
                item.rule_id,
            )

    @staticmethod
    def _set_row(table, row, values, identity) -> None:
        for column, value in enumerate(values):
            cell = QTableWidgetItem(value)
            if column == 0:
                cell.setData(Qt.ItemDataRole.UserRole, identity)
            table.setItem(row, column, cell)

    def _load_class_filters(self) -> None:
        self.class_year_combo.blockSignals(True)
        self.class_grade_combo.blockSignals(True)
        self.class_year_combo.clear()
        for item in self.school_years:
            self.class_year_combo.addItem(item.year_name, item.school_year_id)
        current = next(
            (item.school_year_id for item in self.school_years if item.is_current),
            None,
        )
        if current is not None:
            self.class_year_combo.setCurrentIndex(
                self.class_year_combo.findData(current)
            )
        self.class_grade_combo.clear()
        self.class_grade_combo.addItem("Tất cả khối", None)
        for item in self.grades:
            self.class_grade_combo.addItem(
                item.grade_name or f"Khối {item.grade_number}",
                item.grade_id,
            )
        self.class_year_combo.blockSignals(False)
        self.class_grade_combo.blockSignals(False)

    def _load_advanced_filters(self) -> None:
        current_year_id = next(
            (item.school_year_id for item in self.school_years if item.is_current),
            None,
        )
        for combo in (self.assessment_year_combo, self.rule_year_combo):
            combo.blockSignals(True)
            combo.clear()
            for item in self.school_years:
                combo.addItem(item.year_name, item.school_year_id)
            if current_year_id is not None:
                combo.setCurrentIndex(combo.findData(current_year_id))
            combo.blockSignals(False)
        for combo in (self.assessment_subject_combo, self.rule_subject_combo):
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("Tất cả môn", None)
            for item in self.subjects:
                combo.addItem(item.subject_name, item.subject_id)
            combo.blockSignals(False)

    def create_school_year(self, *_args) -> bool:
        dialog = self.school_year_dialog_factory(None, self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return False
        return self._write(lambda: self.academic_service.create_school_year(*dialog.values()))

    def edit_school_year(self, *_args) -> bool:
        item = self._selected(self.school_year_table, self.school_years, "school_year_id")
        if item is None:
            return False
        dialog = self.school_year_dialog_factory(item, self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return False
        return self._write(
            lambda: self.academic_service.update_school_year(
                item.school_year_id,
                *dialog.values(),
            )
        )

    def create_grade(self, *_args) -> bool:
        dialog = self.grade_dialog_factory(None, self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return False
        return self._write(lambda: self.academic_service.create_grade(*dialog.values()))

    def edit_grade(self, *_args) -> bool:
        item = self._selected(self.grade_table, self.grades, "grade_id")
        if item is None:
            return False
        dialog = self.grade_dialog_factory(item, self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return False
        _, grade_name = dialog.values()
        return self._write(
            lambda: self.academic_service.update_grade_name(
                item.grade_id,
                grade_name,
            )
        )

    def create_class(self, *_args) -> bool:
        dialog = self.class_dialog_factory(
            list(self.school_years),
            list(self.grades),
            None,
            self,
        )
        if dialog.exec() != dialog.DialogCode.Accepted:
            return False
        class_name, grade_id, year_id, teacher, status = dialog.values()
        return self._write(
            lambda: self.academic_service.create_class(
                class_name,
                grade_id,
                year_id,
                teacher,
                status,
            )
        )

    def edit_class(self, *_args) -> bool:
        item = self._selected(self.class_table, self.classes, "class_id")
        if item is None:
            return False
        dialog = self.class_dialog_factory(
            list(self.school_years),
            list(self.grades),
            item,
            self,
        )
        if dialog.exec() != dialog.DialogCode.Accepted:
            return False
        return self._write(
            lambda: self.academic_service.update_class(
                item.class_id,
                *dialog.values(),
            )
        )

    def toggle_class_active(self, *_args) -> bool:
        item = self._selected(self.class_table, self.classes, "class_id")
        if item is None:
            return False
        return self._write(
            lambda: self.academic_service.set_class_active(
                item.class_id,
                not item.is_active,
            )
        )

    def create_subject(self, *_args) -> bool:
        dialog = self.subject_dialog_factory(None, self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return False
        return self._write(
            lambda: self.academic_service.create_subject(*dialog.values())
        )

    def edit_subject(self, *_args) -> bool:
        item = self._selected(self.subject_table, self.subjects, "subject_id")
        if item is None:
            return False
        dialog = self.subject_dialog_factory(item, self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return False
        return self._write(
            lambda: self.academic_service.update_subject(
                item.subject_id,
                *dialog.values(),
            )
        )

    def toggle_subject_active(self, *_args) -> bool:
        item = self._selected(self.subject_table, self.subjects, "subject_id")
        if item is None:
            return False
        return self._write(
            lambda: self.academic_service.set_subject_active(
                item.subject_id,
                not item.is_active,
            )
        )

    def create_assessment(self, *_args) -> bool:
        dialog = self.assessment_dialog_factory(
            list(self.school_years),
            list(self.subjects),
            None,
            self,
        )
        if dialog.exec() != dialog.DialogCode.Accepted:
            return False
        values = dialog.values()
        return self._write(
            lambda: self.academic_service.create_assessment(*values[:-1])
        )

    def edit_assessment(self, *_args) -> bool:
        item = self._selected(
            self.assessment_table,
            self.assessments,
            "assessment_id",
        )
        if item is None:
            return False
        dialog = self.assessment_dialog_factory(
            list(self.school_years),
            list(self.subjects),
            item,
            self,
        )
        if dialog.exec() != dialog.DialogCode.Accepted:
            return False
        return self._write(
            lambda: self.academic_service.update_assessment(
                item.assessment_id,
                *dialog.values(),
            )
        )

    def toggle_assessment_active(self, *_args) -> bool:
        item = self._selected(
            self.assessment_table,
            self.assessments,
            "assessment_id",
        )
        if item is None:
            return False
        return self._write(
            lambda: self.academic_service.set_assessment_active(
                item.assessment_id,
                item.status != AssessmentStatus.ACTIVE,
            )
        )

    def create_support_rule(self, *_args) -> bool:
        dialog = self.support_rule_dialog_factory(
            list(self.school_years),
            list(self.subjects),
            None,
            self,
        )
        if dialog.exec() != dialog.DialogCode.Accepted:
            return False
        return self._write(
            lambda: self.academic_service.create_support_rule(*dialog.values())
        )

    def edit_support_rule(self, *_args) -> bool:
        item = self._selected(self.rule_table, self.support_rules, "rule_id")
        if item is None:
            return False
        dialog = self.support_rule_dialog_factory(
            list(self.school_years),
            list(self.subjects),
            item,
            self,
        )
        if dialog.exec() != dialog.DialogCode.Accepted:
            return False
        _subject_id, _year_id, threshold, _active = dialog.values()
        return self._write(
            lambda: self.academic_service.update_support_rule_threshold(
                item.rule_id,
                threshold,
            )
        )

    def toggle_support_rule_active(self, *_args) -> bool:
        item = self._selected(self.rule_table, self.support_rules, "rule_id")
        if item is None:
            return False
        return self._write(
            lambda: self.academic_service.set_support_rule_active(
                item.rule_id,
                not item.is_active,
            )
        )

    def _write(self, operation) -> bool:
        if self.academic_service is None:
            return False
        try:
            operation()
        except AppError as exc:
            self._show_error(str(exc))
            return False
        except Exception:
            self._show_error()
            return False
        return self.initialize_catalogs()

    @staticmethod
    def _selected(table, items, id_field):
        row = table.currentRow()
        if row < 0:
            return None
        identity = table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        return next(
            (item for item in items if getattr(item, id_field) == identity),
            None,
        )

    def _show_error(self, message="Không thể tải hoặc cập nhật danh mục.") -> None:
        self.state_label.setText(message)
