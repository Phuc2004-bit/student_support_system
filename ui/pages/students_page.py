from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QFrame,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QHBoxLayout,
    QHeaderView,
    QSplitter,
    QStackedLayout,
    QWidget,
)

from models.dto.enrollment import EnrollmentListItem
from models.dto.student_filter import StudentFilter
from models.dto.student_list import StudentListItem
from models.dto.data_export import StudentExportContext
from services.data_export_contract import StudentExportServiceContract
from ui.action_permissions import action_is_allowed, apply_action_permission
from services.enrollment_contract import EnrollmentServiceContract
from services.student_contract import (
    StudentListServiceContract,
    StudentServiceContract,
)
from services.student_profile_contract import (
    StudentProfileServiceContract,
)
from ui.dialogs.enrollment_dialog import EnrollmentDialog
from ui.dialogs.student_form_dialog import StudentFormDialog
from ui.dialogs.student_profile_dialog import StudentProfileDialog
from ui.widgets.current_enrollment_widget import (
    CurrentEnrollmentWidget,
)
from ui.widgets.enrollment_history_widget import (
    EnrollmentHistoryWidget,
)
from ui.widgets.student_filter_widget import StudentFilterWidget
from ui.theme import status_badge_colors, student_page_stylesheet


def student_status_label(status) -> str:
    value = getattr(status, "value", status)
    return {
        "ACTIVE": "Đang học",
        "INACTIVE": "Ngừng hoạt động",
    }.get(str(value), str(value))


def enrollment_is_active(item: EnrollmentListItem) -> bool:
    value = getattr(item.status, "value", item.status)
    return str(value) == "ACTIVE"


class StudentsPage(QWidget):
    add_student_requested = Signal()
    refresh_requested = Signal()
    student_requested = Signal(str)
    student_saved = Signal(str)
    enrollment_saved = Signal(str)

    TABLE_HEADERS = (
        "Mã học sinh",
        "Họ và tên",
        "Ngày sinh",
        "Giới tính",
        "Lớp hiện tại",
        "Trạng thái",
    )

    def __init__(
        self,
        student_service: StudentListServiceContract | None = None,
        academic_service=None,
        student_crud_service: StudentServiceContract | None = None,
        dialog_factory=StudentFormDialog,
        enrollment_service: EnrollmentServiceContract | None = None,
        enrollment_dialog_factory=EnrollmentDialog,
        student_profile_service: StudentProfileServiceContract | None = None,
        profile_dialog_factory=StudentProfileDialog,
        parent: QWidget | None = None,
        student_export_service: StudentExportServiceContract | None = None,
        excel_permission_check=None,
    ) -> None:
        super().__init__(parent)

        self.student_service = student_service
        self.student_crud_service = student_crud_service
        self.academic_service = academic_service
        self.dialog_factory = dialog_factory
        self.enrollment_service = enrollment_service
        self.enrollment_dialog_factory = enrollment_dialog_factory
        self.student_profile_service = student_profile_service
        self.profile_dialog_factory = profile_dialog_factory
        self.student_export_service = student_export_service
        self.excel_permission_check = excel_permission_check

        self._items: tuple[StudentListItem, ...] = ()
        self._last_filter = StudentFilter()
        self._current_enrollment: EnrollmentListItem | None = None
        self._enrollment_history: tuple[EnrollmentListItem, ...] = ()

        self.setObjectName("studentsPage")
        self.setStyleSheet(student_page_stylesheet())
        self._build_ui()
        self._connect_signals()
        apply_action_permission(
            self.export_button,
            self.excel_permission_check,
        )

    @property
    def items(self) -> tuple[StudentListItem, ...]:
        return self._items

    @property
    def last_filter(self) -> StudentFilter:
        return self._last_filter

    @property
    def current_enrollment(
        self,
    ) -> EnrollmentListItem | None:
        return self._current_enrollment

    @property
    def enrollment_history(
        self,
    ) -> tuple[EnrollmentListItem, ...]:
        return self._enrollment_history

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 24)
        root.setSpacing(14)

        self.title_label = QLabel("Học sinh", self)
        self.subtitle_label = QLabel(
            "Quản lý hồ sơ và lớp học của học sinh",
            self,
        )
        self.title_label.setVisible(False)
        self.subtitle_label.setVisible(False)

        self.toolbar_frame = QFrame(self)
        self.toolbar_frame.setObjectName("studentsToolbarFrame")
        toolbar_layout = QVBoxLayout(self.toolbar_frame)
        toolbar_layout.setContentsMargins(16, 14, 16, 14)
        toolbar_layout.setSpacing(12)

        self.filter_widget = StudentFilterWidget(
            academic_service=self.academic_service,
            parent=self.toolbar_frame,
        )
        self.search_input = self.filter_widget.search_input
        toolbar_layout.addWidget(self.filter_widget)

        self.refresh_button = QPushButton("Làm mới", self)
        self.export_button = QPushButton("Xuất Excel", self)
        self.export_button.setObjectName("exportStudentsExcelButton")
        self.edit_button = QPushButton("Sửa học sinh", self)
        self.profile_button = QPushButton("Xem hồ sơ", self)
        self.add_button = QPushButton("+ Thêm học sinh", self)
        self.add_button.setObjectName("addStudentButton")
        self.add_button.setProperty("variant", "primary")
        self.export_button.setProperty("variant", "secondary")
        self.refresh_button.setProperty("variant", "secondary")
        self.edit_button.setProperty("variant", "secondary")
        self.profile_button.setProperty("variant", "secondary")
        for button in (
            self.add_button,
            self.export_button,
            self.refresh_button,
            self.edit_button,
            self.profile_button,
        ):
            button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.edit_button.setEnabled(False)
        self.profile_button.setEnabled(False)

        toolbar_actions = QHBoxLayout()
        toolbar_actions.setSpacing(10)
        toolbar_actions.addWidget(self.add_button)
        toolbar_actions.addWidget(self.export_button)
        toolbar_actions.addWidget(self.refresh_button)
        toolbar_actions.addStretch(1)
        toolbar_layout.addLayout(toolbar_actions)
        root.addWidget(self.toolbar_frame)

        self.content_splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.content_splitter.setObjectName("studentsContentSplitter")
        self.content_splitter.setChildrenCollapsible(False)

        self.table_card = QFrame(self.content_splitter)
        self.table_card.setObjectName("studentsTableCard")
        table_card_layout = QVBoxLayout(self.table_card)
        table_card_layout.setContentsMargins(14, 12, 14, 14)
        table_card_layout.setSpacing(10)

        table_header = QHBoxLayout()
        self.summary_prefix_label = QLabel("Tổng:", self.table_card)
        self.summary_prefix_label.setObjectName("studentsCountLabel")
        self.count_label = QLabel("0 học sinh", self.table_card)
        self.count_label.setObjectName("studentsCountLabel")
        table_header.addWidget(self.summary_prefix_label)
        table_header.addWidget(self.count_label)
        table_header.addStretch(1)
        table_header.addWidget(self.profile_button)
        table_header.addWidget(self.edit_button)
        table_card_layout.addLayout(table_header)

        self.table_host = QWidget(self.table_card)
        self.table_host.setObjectName("studentsTableHost")
        self.table_stack = QStackedLayout(self.table_host)
        self.table_stack.setContentsMargins(0, 0, 0, 0)

        self.table = QTableWidget(self.table_host)
        self.table.setObjectName("studentsTable")
        self.table.setColumnCount(len(self.TABLE_HEADERS))
        self.table.setHorizontalHeaderLabels(self.TABLE_HEADERS)
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setWordWrap(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(40)

        header = self.table.horizontalHeader()
        header.setMinimumHeight(42)
        header.setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        header.setSectionResizeMode(
            1,
            QHeaderView.ResizeMode.Stretch,
        )

        self.empty_widget = QWidget(self.table_host)
        self.empty_widget.setObjectName("studentsEmptyState")
        empty_layout = QVBoxLayout(self.empty_widget)
        empty_layout.setContentsMargins(24, 24, 24, 24)
        empty_layout.addStretch(1)
        self.empty_title_label = QLabel("Chưa có học sinh", self.empty_widget)
        self.empty_title_label.setObjectName("studentsEmptyTitle")
        self.empty_title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_description_label = QLabel(
            "Thêm học sinh hoặc thay đổi bộ lọc để bắt đầu.",
            self.empty_widget,
        )
        self.empty_description_label.setObjectName("studentsEmptyDescription")
        self.empty_description_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(self.empty_title_label)
        empty_layout.addWidget(self.empty_description_label)
        empty_layout.addStretch(1)

        self.table_stack.addWidget(self.table)
        self.table_stack.addWidget(self.empty_widget)
        self.table_stack.setCurrentWidget(self.empty_widget)
        table_card_layout.addWidget(self.table_host, 1)

        self.details_card = QFrame(self.content_splitter)
        self.details_card.setObjectName("studentsDetailsCard")
        details_layout = QVBoxLayout(self.details_card)
        details_layout.setContentsMargins(14, 12, 14, 14)
        details_layout.setSpacing(10)
        self.details_title_label = QLabel("Thông tin lớp học", self.details_card)
        self.details_title_label.setObjectName("studentsDetailsTitle")
        details_layout.addWidget(self.details_title_label)

        self.current_enrollment_widget = CurrentEnrollmentWidget(self.details_card)
        self.enrollment_history_widget = EnrollmentHistoryWidget(self.details_card)
        details_layout.addWidget(self.current_enrollment_widget)
        details_layout.addWidget(self.enrollment_history_widget, 1)

        self.content_splitter.addWidget(self.table_card)
        self.content_splitter.addWidget(self.details_card)
        self.content_splitter.setStretchFactor(0, 3)
        self.content_splitter.setStretchFactor(1, 2)
        self.content_splitter.setSizes((760, 360))
        root.addWidget(self.content_splitter, 1)

    def _connect_signals(self) -> None:
        self.add_button.clicked.connect(
            self._create_student
        )
        self.edit_button.clicked.connect(
            self._edit_selected_student
        )
        self.profile_button.clicked.connect(
            self._show_selected_profile
        )
        self.refresh_button.clicked.connect(
            self.refresh_students
        )
        self.export_button.clicked.connect(
            lambda _checked=False: self.export_students()
        )
        self.filter_widget.filters_changed.connect(
            self._on_filters_changed
        )
        self.table.cellDoubleClicked.connect(
            self._on_row_activated
        )
        self.table.itemSelectionChanged.connect(
            self._selection_changed
        )
        self.current_enrollment_widget.assign_requested.connect(
            self._assign_selected_student
        )
        self.current_enrollment_widget.transfer_requested.connect(
            self._transfer_selected_student
        )

    def initialize_students(self) -> bool:
        if self.academic_service is not None:
            self.filter_widget.load_options()
            return True

        return self.refresh_students()

    def load_students(self) -> bool:
        return self.refresh_students()

    def student_export_context(self) -> StudentExportContext:
        filters = self.filter_widget.current_value()
        return StudentExportContext(
            filters=filters,
            school_year_name=(
                self.filter_widget.school_year_combo.currentText()
                if filters.school_year_id is not None
                else None
            ),
            grade_name=(
                self.filter_widget.grade_combo.currentText()
                if filters.grade_id is not None
                else None
            ),
            class_name=(
                self.filter_widget.class_combo.currentText()
                if filters.class_id is not None
                else None
            ),
        )

    def export_students(self) -> bool:
        if not action_is_allowed(self.excel_permission_check):
            self._show_error(
                "Không có quyền",
                PermissionError("Bạn không có quyền xuất danh sách học sinh."),
            )
            return False
        if self.student_export_service is None:
            self._show_error(
                "Xuất Excel",
                RuntimeError("Chưa có dịch vụ xuất danh sách học sinh."),
            )
            return False
        output_path, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "Xuất danh sách học sinh",
            "danh_sach_hoc_sinh.xlsx",
            "Excel Workbook (*.xlsx)",
        )
        if not output_path:
            return False
        if not output_path.lower().endswith(".xlsx"):
            output_path += ".xlsx"
        try:
            self.student_export_service.export_xlsx(
                self.student_export_context(),
                output_path,
            )
        except Exception as exc:
            self._show_error("Không thể xuất Excel", exc)
            return False
        QMessageBox.information(
            self,
            "Xuất Excel",
            "Đã xuất danh sách học sinh thành công.",
        )
        return True

    def refresh_students(self) -> bool:
        self.refresh_requested.emit()

        if self.student_service is None:
            return False

        filters = self.filter_widget.current_value()
        self._last_filter = filters

        items = self.student_service.list_students(filters)
        self.set_students(items)
        return True

    def _on_filters_changed(
        self,
        filters: StudentFilter,
    ) -> None:
        self._last_filter = filters

        if self.student_service is None:
            return

        items = self.student_service.list_students(filters)
        self.set_students(items)

    def set_students(
        self,
        items: Iterable[StudentListItem],
    ) -> None:
        self._items = tuple(items)

        self.table.blockSignals(True)
        self.table.clearSelection()
        self.table.setRowCount(len(self._items))

        for row, item in enumerate(self._items):
            values = (
                item.student_code,
                item.full_name,
                (
                    item.date_of_birth.strftime("%d/%m/%Y")
                    if item.date_of_birth
                    else "—"
                ),
                item.gender or "—",
                item.current_class_name or "Chưa xếp lớp",
                student_status_label(item.status),
            )

            for column, value in enumerate(values):
                cell = QTableWidgetItem(str(value))
                if column != 1:
                    cell.setTextAlignment(
                        Qt.AlignmentFlag.AlignCenter
                    )
                if column == 5:
                    foreground, background = status_badge_colors(item.status)
                    cell.setForeground(QColor(foreground))
                    cell.setBackground(QColor(background))
                self.table.setItem(row, column, cell)

        self.table.blockSignals(False)
        self.table_stack.setCurrentWidget(
            self.table if self._items else self.empty_widget
        )

        self.set_student_count(len(self._items))
        self._clear_current_enrollment()
        self._update_action_state()

    def set_student_count(self, count: int) -> None:
        if count < 0:
            raise ValueError(
                "Số lượng học sinh không được âm."
            )

        self.count_label.setText(
            f"{count:,}".replace(",", ".") + " học sinh"
        )

    def student_id_at_row(
        self,
        row: int,
    ) -> str | None:
        if row < 0 or row >= len(self._items):
            return None
        return self._items[row].student_id

    def selected_student_id(self) -> str | None:
        return self.student_id_at_row(
            self.table.currentRow()
        )

    def _selection_changed(self) -> None:
        self._update_action_state()
        self._load_selected_enrollment()

    def _update_action_state(self) -> None:
        self.edit_button.setEnabled(
            self.selected_student_id() is not None
        )
        self.profile_button.setEnabled(
            self.selected_student_id() is not None
            and self.student_profile_service is not None
        )

    def _clear_current_enrollment(self) -> None:
        self._current_enrollment = None
        self.current_enrollment_widget.set_enrollment(None)
        self._enrollment_history = ()
        self.enrollment_history_widget.set_history(())

    def _load_selected_enrollment(self) -> bool:
        student_id = self.selected_student_id()

        if (
            student_id is None
            or self.enrollment_service is None
        ):
            self._clear_current_enrollment()
            return False

        try:
            history = self.enrollment_service.get_student_history(
                student_id
            )
        except Exception as exc:
            self._clear_current_enrollment()
            self._show_error(
                "Không thể tải lớp hiện tại",
                exc,
            )
            return False

        self._enrollment_history = tuple(history)
        self.enrollment_history_widget.set_history(history)

        active = next(
            (
                item
                for item in self._enrollment_history
                if enrollment_is_active(item)
            ),
            None,
        )

        self._current_enrollment = active
        self.current_enrollment_widget.set_enrollment(active)
        return True

    def _refresh_and_reselect(
        self,
        student_id: str,
    ) -> None:
        self.refresh_students()

        for row, item in enumerate(self._items):
            if item.student_id == student_id:
                self.table.selectRow(row)
                return

    def _assign_selected_student(self) -> bool:
        student_id = self.selected_student_id()

        if (
            student_id is None
            or self.enrollment_service is None
        ):
            return False

        if self._current_enrollment is not None:
            QMessageBox.warning(
                self,
                "Không thể xếp lớp",
                "Học sinh đã có lớp hiện tại. Hãy dùng Chuyển lớp.",
            )
            return False

        dialog = self.enrollment_dialog_factory(
            academic_service=self.academic_service,
            mode=EnrollmentDialog.MODE_ASSIGN,
            parent=self,
        )
        dialog.load_options()

        if dialog.exec() != dialog.DialogCode.Accepted:
            return False

        try:
            self.enrollment_service.enroll_student(
                student_id,
                dialog.selected_class_id(),
                dialog.action_date(),
            )
        except Exception as exc:
            self._show_error(
                "Không thể xếp lớp",
                exc,
            )
            return False

        self._refresh_and_reselect(student_id)
        self.enrollment_saved.emit(student_id)

        QMessageBox.information(
            self,
            "Thành công",
            "Đã xếp lớp cho học sinh.",
        )
        return True

    def _transfer_selected_student(self) -> bool:
        student_id = self.selected_student_id()

        if (
            student_id is None
            or self.enrollment_service is None
            or self._current_enrollment is None
        ):
            return False

        dialog = self.enrollment_dialog_factory(
            academic_service=self.academic_service,
            mode=EnrollmentDialog.MODE_TRANSFER,
            current_class_id=self._current_enrollment.class_id,
            parent=self,
        )
        dialog.load_options()

        if dialog.exec() != dialog.DialogCode.Accepted:
            return False

        try:
            self.enrollment_service.transfer_student(
                student_id,
                dialog.selected_class_id(),
                dialog.action_date(),
            )
        except Exception as exc:
            self._show_error(
                "Không thể chuyển lớp",
                exc,
            )
            return False

        self._refresh_and_reselect(student_id)
        self.enrollment_saved.emit(student_id)

        QMessageBox.information(
            self,
            "Thành công",
            "Đã chuyển lớp cho học sinh.",
        )
        return True

    def _create_student(self) -> bool:
        self.add_student_requested.emit()

        if self.student_crud_service is None:
            return False

        dialog = self.dialog_factory(parent=self)

        if dialog.exec() != dialog.DialogCode.Accepted:
            return False

        try:
            created = self.student_crud_service.create_student(
                dialog.create_data()
            )
        except Exception as exc:
            self._show_error(
                "Không thể thêm học sinh",
                exc,
            )
            return False

        self.refresh_students()
        self.student_saved.emit(created.student_id)

        QMessageBox.information(
            self,
            "Thành công",
            "Đã thêm học sinh.",
        )
        return True

    def _edit_selected_student(self) -> bool:
        student_id = self.selected_student_id()

        if (
            student_id is None
            or self.student_crud_service is None
        ):
            return False

        try:
            student = self.student_crud_service.get_student(
                student_id
            )
        except Exception as exc:
            self._show_error(
                "Không thể tải học sinh",
                exc,
            )
            return False

        dialog = self.dialog_factory(
            student=student,
            parent=self,
        )

        if dialog.exec() != dialog.DialogCode.Accepted:
            return False

        try:
            updated = self.student_crud_service.update_student(
                student_id,
                dialog.update_data(),
            )
        except Exception as exc:
            self._show_error(
                "Không thể cập nhật học sinh",
                exc,
            )
            return False

        self._refresh_and_reselect(student_id)
        self.student_saved.emit(updated.student_id)

        QMessageBox.information(
            self,
            "Thành công",
            "Đã cập nhật học sinh.",
        )
        return True

    def _show_selected_profile(self) -> bool:
        student_id = self.selected_student_id()

        if (
            student_id is None
            or self.student_profile_service is None
        ):
            return False

        dialog = self.profile_dialog_factory(
            student_id=student_id,
            profile_service=self.student_profile_service,
            parent=self,
        )

        try:
            dialog.load_profile()
        except Exception as exc:
            self._show_error(
                "Không thể tải hồ sơ học sinh",
                exc,
            )
            return False

        dialog.exec()
        return True

    @staticmethod
    def _error_message(exc: Exception) -> str:
        text = str(exc).strip()
        return text or "Đã xảy ra lỗi không xác định."

    def _show_error(
        self,
        title: str,
        exc: Exception,
    ) -> None:
        QMessageBox.warning(
            self,
            title,
            self._error_message(exc),
        )

    def _on_row_activated(
        self,
        row: int,
        _column: int,
    ) -> None:
        student_id = self.student_id_at_row(row)

        if student_id is not None:
            self.student_requested.emit(student_id)
            self._show_selected_profile()
