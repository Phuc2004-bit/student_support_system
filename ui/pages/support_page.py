from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QFrame,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QToolButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from models.dto.report_dto import SupportReportRow
from models.dto.report_export import SupportReportExportData
from exceptions import ReportExportError, ValidationError
from ui.action_permissions import action_is_allowed, apply_action_permission
from services.support_read_contract import (
    InterventionDetailServiceContract,
    SupportReadServiceContract,
)
from services.support_contract import (
    InterventionContinueServiceContract,
    InterventionPlanningServiceContract,
    InterventionReviewServiceContract,
    InterventionStartServiceContract,
    InterventionWaitingReviewServiceContract,
)
from services.user_contract import ResponsibleUserServiceContract
from ui.dialogs.intervention_detail_dialog import (
    InterventionDetailDialog,
)
from ui.widgets.dashboard_charts import status_label
from ui.widgets.support_filter_widget import (
    SupportFilterSelection,
    SupportFilterWidget,
)
from ui.theme import status_badge_colors, support_page_stylesheet


class SupportPage(QWidget):
    intervention_requested = Signal(int)

    STATE_IDLE = "idle"
    STATE_LOADING = "loading"
    STATE_SUCCESS = "success"
    STATE_EMPTY = "empty"
    STATE_ERROR = "error"

    TABLE_HEADERS = (
        "STT",
        "Mã học sinh",
        "Họ và tên",
        "Khối",
        "Lớp",
        "Môn",
        "Điểm phát hiện",
        "Ngày phát hiện",
        "Trạng thái",
        "Người phụ trách",
    )

    EMPTY_MESSAGE = (
        "Chưa có học sinh cần bổ trợ theo bộ lọc hiện tại."
    )

    def __init__(
        self,
        academic_service=None,
        support_read_service: SupportReadServiceContract | None = None,
        intervention_detail_service:
            InterventionDetailServiceContract | None = None,
        intervention_planning_service:
            InterventionPlanningServiceContract | None = None,
        intervention_start_service:
            InterventionStartServiceContract | None = None,
        intervention_waiting_review_service:
            InterventionWaitingReviewServiceContract | None = None,
        intervention_review_service:
            InterventionReviewServiceContract | None = None,
        intervention_continue_service:
            InterventionContinueServiceContract | None = None,
        assessment_service=None,
        user_service: ResponsibleUserServiceContract | None = None,
        detail_dialog_factory=InterventionDetailDialog,
        parent: QWidget | None = None,
        support_report_service=None,
        report_export_service=None,
        excel_permission_check=None,
    ) -> None:
        super().__init__(parent)
        self.academic_service = academic_service
        self.support_read_service = support_read_service
        self.intervention_detail_service = intervention_detail_service
        self.intervention_planning_service = intervention_planning_service
        self.intervention_start_service = intervention_start_service
        self.intervention_waiting_review_service = (
            intervention_waiting_review_service
        )
        self.intervention_review_service = intervention_review_service
        self.intervention_continue_service = intervention_continue_service
        self.assessment_service = assessment_service
        self.user_service = user_service
        self.detail_dialog_factory = detail_dialog_factory
        self.support_report_service = (
            support_report_service or support_read_service
        )
        self.report_export_service = report_export_service
        self.excel_permission_check = excel_permission_check
        self._items: tuple[SupportReportRow, ...] = ()
        self._load_state = self.STATE_IDLE
        self.setObjectName("supportPage")
        self._build_ui()
        self.setStyleSheet(support_page_stylesheet())
        self._connect_signals()
        apply_action_permission(
            self.export_button,
            self.excel_permission_check,
        )

    @property
    def items(self) -> tuple[SupportReportRow, ...]:
        return self._items

    @property
    def load_state(self) -> str:
        return self._load_state

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 20)
        root.setSpacing(12)

        heading = QHBoxLayout()
        titles = QVBoxLayout()
        self.title_label = QLabel("Bổ trợ học tập", self)
        self.subtitle_label = QLabel(
            "Theo dõi tiến trình từ phát hiện đến đánh giá kết quả.",
            self,
        )
        self.title_label.setObjectName("supportPageTitle")
        self.subtitle_label.setObjectName("supportPageSubtitle")
        # MainWindow already provides the page title and subtitle. Keep these
        # labels for the standalone-page contract without duplicating headings.
        self.title_label.setVisible(False)
        self.subtitle_label.setVisible(False)
        titles.addWidget(self.title_label)
        titles.addWidget(self.subtitle_label)
        heading.addLayout(titles)
        heading.addStretch(1)
        self.refresh_button = QPushButton("Làm mới", self)
        self.refresh_button.setObjectName("supportRefreshButton")
        self.export_button = QToolButton(self)
        self.export_button.setText("Xuất Excel")
        self.export_button.setObjectName("exportSupportExcelButton")
        self.export_button.setProperty("variant", "primary")
        heading.addWidget(self.export_button)
        heading.addWidget(self.refresh_button)
        root.addLayout(heading)

        self.filter_frame = QFrame(self)
        self.filter_frame.setObjectName("supportFilterCard")
        filter_layout = QVBoxLayout(self.filter_frame)
        filter_layout.setContentsMargins(16, 14, 16, 16)
        filter_layout.setSpacing(10)
        self.filter_caption = QLabel("BỘ LỌC HỒ SƠ", self.filter_frame)
        self.filter_caption.setObjectName("supportFilterCaption")
        filter_layout.addWidget(self.filter_caption)
        self.filter_widget = SupportFilterWidget(
            academic_service=self.academic_service,
            parent=self.filter_frame,
        )
        filter_layout.addWidget(self.filter_widget)
        root.addWidget(self.filter_frame)

        self.school_year_combo = self.filter_widget.school_year_combo
        self.grade_combo = self.filter_widget.grade_combo
        self.class_combo = self.filter_widget.class_combo
        self.subject_combo = self.filter_widget.subject_combo
        self.status_combo = self.filter_widget.status_combo

        self.state_label = QLabel(self)
        self.state_label.setObjectName("supportStateLabel")
        self.state_label.setWordWrap(True)
        root.addWidget(self.state_label)

        self.table_frame = QFrame(self)
        self.table_frame.setObjectName("supportTableFrame")
        table_layout = QVBoxLayout(self.table_frame)
        table_layout.setContentsMargins(0, 0, 0, 0)
        table_layout.setSpacing(0)

        table_header = QHBoxLayout()
        table_header.setContentsMargins(16, 12, 16, 10)
        self.table_caption = QLabel("HỒ SƠ BỔ TRỢ", self.table_frame)
        self.table_caption.setObjectName("supportTableCaption")
        table_header.addWidget(self.table_caption)
        table_header.addStretch(1)
        self.count_label = QLabel("0 hồ sơ bổ trợ", self.table_frame)
        self.count_label.setObjectName("supportCountLabel")
        table_header.addWidget(self.count_label)
        table_layout.addLayout(table_header)

        self.empty_container = QWidget(self.table_frame)
        empty_layout = QVBoxLayout(self.empty_container)
        empty_layout.setContentsMargins(24, 56, 24, 56)
        self.empty_title_label = QLabel(
            "Chưa có hồ sơ phù hợp",
            self.empty_container,
        )
        self.empty_title_label.setObjectName("supportEmptyTitle")
        self.empty_title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label = QLabel(self.EMPTY_MESSAGE, self.empty_container)
        self.empty_label.setObjectName("supportEmptyDescription")
        self.empty_label.setWordWrap(True)
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addStretch(1)
        empty_layout.addWidget(self.empty_title_label)
        empty_layout.addWidget(self.empty_label)
        empty_layout.addStretch(1)
        table_layout.addWidget(self.empty_container, 1)

        self.table = QTableWidget(self.table_frame)
        self.table.setObjectName("supportTable")
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
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        table_layout.addWidget(self.table, 1)
        root.addWidget(self.table_frame, 1)

        self._show_empty(self.EMPTY_MESSAGE)

    def _connect_signals(self) -> None:
        self.filter_widget.filters_changed.connect(
            self._on_filters_changed
        )
        self.refresh_button.clicked.connect(
            self.refresh_support_cases
        )
        self.export_button.clicked.connect(
            lambda _checked=False: self.export_support_cases()
        )
        self.table.cellDoubleClicked.connect(
            self._on_row_activated
        )

    def initialize_support(self) -> bool:
        if self.academic_service is None:
            self._show_empty("Chưa có dữ liệu bộ lọc học vụ.")
            return False

        try:
            self.filter_widget.load_options()
        except Exception:
            self._show_error()
            return False
        return True

    def current_filters(self) -> SupportFilterSelection:
        return self.filter_widget.current_value()

    def refresh_support_cases(self, *_args) -> bool:
        filters = self.current_filters()
        if filters.school_year_id is None:
            self._show_empty("Vui lòng chọn năm học để tải dữ liệu bổ trợ.")
            return False
        if self.support_read_service is None:
            self._show_empty("Chưa có dịch vụ đọc dữ liệu bổ trợ.")
            return False

        self._show_loading()
        try:
            rows = self.support_read_service.get_support_cases(
                school_year_id=filters.school_year_id,
                grade_id=filters.grade_id,
                class_id=filters.class_id,
                subject_id=filters.subject_id,
                status=filters.status,
            )
        except Exception:
            self._show_error()
            return False

        self.set_support_cases(rows)
        return True

    def set_support_cases(
        self,
        rows: Iterable[SupportReportRow],
    ) -> None:
        self._items = tuple(rows)
        self.table.setRowCount(len(self._items))

        for row_index, item in enumerate(self._items):
            cells = (
                str(row_index + 1),
                item.student_code,
                item.full_name,
                str(item.grade_number),
                item.class_name,
                item.subject_name,
                str(item.trigger_score),
                item.detected_date.strftime("%d/%m/%Y"),
                status_label(item.status),
                item.responsible_user_name or "—",
            )
            for column, text in enumerate(cells):
                table_item = QTableWidgetItem(text)
                if column == 0:
                    table_item.setData(
                        Qt.ItemDataRole.UserRole,
                        item.intervention_id,
                    )
                if column in (0, 3, 4, 6, 7, 8):
                    table_item.setTextAlignment(
                        Qt.AlignmentFlag.AlignCenter
                    )
                if column == 8:
                    foreground, background = status_badge_colors(
                        item.status
                    )
                    table_item.setForeground(QColor(foreground))
                    table_item.setBackground(QColor(background))
                    table_item.setData(
                        Qt.ItemDataRole.UserRole + 1,
                        str(getattr(item.status, "value", item.status)),
                    )
                self.table.setItem(row_index, column, table_item)

        self.count_label.setText(
            f"{len(self._items)} hồ sơ bổ trợ"
        )
        if self._items:
            self._load_state = self.STATE_SUCCESS
            self.state_label.setText(
                f"Đã tải {len(self._items)} hồ sơ bổ trợ."
            )
            self.empty_container.setVisible(False)
            self.table.setVisible(True)
            self.refresh_button.setEnabled(True)
        else:
            self._show_empty(self.EMPTY_MESSAGE)

    def export_support_cases(self) -> bool:
        if not action_is_allowed(self.excel_permission_check):
            self._show_export_error(
                "Bạn không có quyền xuất danh sách bổ trợ."
            )
            return False
        filters = self.current_filters()
        context = self.filter_widget.export_context()
        if context is None:
            self.state_label.setText(
                "Vui lòng chọn năm học để xuất danh sách bổ trợ."
            )
            return False
        if (
            self.support_report_service is None
            or self.report_export_service is None
        ):
            self._show_export_error(
                "Chưa có đầy đủ dịch vụ xuất danh sách bổ trợ."
            )
            return False
        output_path, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "Xuất danh sách bổ trợ",
            "danh_sach_bo_tro.xlsx",
            "Excel Workbook (*.xlsx)",
        )
        if not output_path:
            return False
        if not output_path.lower().endswith(".xlsx"):
            output_path += ".xlsx"
        try:
            reader = getattr(
                self.support_report_service,
                "get_support_report",
            )
            snapshot = reader(
                school_year_id=filters.school_year_id,
                grade_id=filters.grade_id,
                class_id=filters.class_id,
                subject_id=filters.subject_id,
                status=filters.status,
            )
        except Exception:
            self._show_export_error(
                "Không thể đọc dữ liệu xuất. Vui lòng thử lại."
            )
            return False
        try:
            writer = getattr(
                self.report_export_service,
                "export_" "xlsx",
            )
            writer(
                SupportReportExportData(context=context, report=snapshot),
                output_path,
            )
        except Exception as exc:
            self._show_export_error(self._export_error_message(exc))
            return False
        QMessageBox.information(
            self,
            "Xuất Excel",
            "Đã xuất danh sách bổ trợ Excel thành công.",
        )
        return True

    def _show_export_error(self, message: str) -> None:
        self.state_label.setText(message)
        QMessageBox.warning(self, "Xuất danh sách bổ trợ", message)

    @staticmethod
    def _export_error_message(exc: Exception) -> str:
        if isinstance(exc, (ReportExportError, ValidationError)):
            return str(exc)
        return "Không thể xuất danh sách bổ trợ. Vui lòng thử lại."

    def intervention_id_at_row(self, row: int) -> int | None:
        if row < 0 or row >= self.table.rowCount():
            return None
        item = self.table.item(row, 0)
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _on_row_activated(self, row: int, _column: int) -> None:
        intervention_id = self.intervention_id_at_row(row)
        if intervention_id is not None:
            self.open_intervention_detail(intervention_id)

    def open_intervention_detail(
        self,
        intervention_id: int,
    ) -> bool:
        self.intervention_requested.emit(intervention_id)
        if self.intervention_detail_service is None:
            self.state_label.setText(
                "Chưa có dịch vụ đọc chi tiết hồ sơ bổ trợ."
            )
            return False

        dialog = self.detail_dialog_factory(
            intervention_id=intervention_id,
            intervention_service=self.intervention_detail_service,
            planning_service=self.intervention_planning_service,
            start_service=self.intervention_start_service,
            waiting_review_service=(
                self.intervention_waiting_review_service
            ),
            review_service=self.intervention_review_service,
            continue_service=self.intervention_continue_service,
            assessment_service=self.assessment_service,
            user_service=self.user_service,
            parent=self,
        )
        planned_signal = getattr(dialog, "intervention_planned", None)
        if planned_signal is not None:
            planned_signal.connect(self._on_intervention_planned)
        started_signal = getattr(dialog, "intervention_started", None)
        if started_signal is not None:
            started_signal.connect(self._on_intervention_started)
        waiting_signal = getattr(
            dialog,
            "intervention_waiting_review",
            None,
        )
        if waiting_signal is not None:
            waiting_signal.connect(self._on_intervention_waiting_review)
        reviewed_signal = getattr(dialog, "intervention_reviewed", None)
        if reviewed_signal is not None:
            reviewed_signal.connect(self._on_intervention_reviewed)
        continued_signal = getattr(dialog, "intervention_continued", None)
        if continued_signal is not None:
            continued_signal.connect(self._on_intervention_continued)
        dialog.load_detail()
        dialog.exec()
        return True

    def _on_intervention_planned(self, _intervention_id: int) -> None:
        self.refresh_support_cases()

    def _on_intervention_started(self, _intervention_id: int) -> None:
        self.refresh_support_cases()

    def _on_intervention_waiting_review(
        self,
        _intervention_id: int,
    ) -> None:
        self.refresh_support_cases()

    def _on_intervention_reviewed(self, _intervention_id: int) -> None:
        self.refresh_support_cases()

    def _on_intervention_continued(self, _intervention_id: int) -> None:
        self.refresh_support_cases()

    def _on_filters_changed(
        self,
        _filters: SupportFilterSelection,
    ) -> None:
        self.refresh_support_cases()

    def _show_empty(self, message: str) -> None:
        self._load_state = self.STATE_EMPTY
        self._items = ()
        self.table.setRowCount(0)
        self.table.setVisible(False)
        self.empty_container.setVisible(True)
        self.empty_label.setText(message)
        self.empty_label.setVisible(True)
        self.state_label.setText(message)
        self.count_label.setText("0 hồ sơ bổ trợ")
        self.refresh_button.setEnabled(True)

    def _show_loading(self) -> None:
        self._load_state = self.STATE_LOADING
        self.state_label.setText("Đang tải danh sách bổ trợ...")
        self.refresh_button.setEnabled(False)

    def _show_error(self) -> None:
        message = "Không thể tải danh sách bổ trợ. Vui lòng thử lại."
        self._show_empty(message)
        self._load_state = self.STATE_ERROR
