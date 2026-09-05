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
from models.dto import Grade, SchoolClass, SchoolYear
from services.catalog_contract import CatalogServiceContract
from ui.dialogs.catalog_dialogs import (
    ClassDialog,
    GradeDialog,
    SchoolYearDialog,
)


class CatalogPage(QWidget):
    def __init__(
        self,
        academic_service: CatalogServiceContract | None = None,
        school_year_dialog_factory=SchoolYearDialog,
        grade_dialog_factory=GradeDialog,
        class_dialog_factory=ClassDialog,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.academic_service = academic_service
        self.school_year_dialog_factory = school_year_dialog_factory
        self.grade_dialog_factory = grade_dialog_factory
        self.class_dialog_factory = class_dialog_factory
        self.school_years: tuple[SchoolYear, ...] = ()
        self.grades: tuple[Grade, ...] = ()
        self.classes: tuple[SchoolClass, ...] = ()
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
