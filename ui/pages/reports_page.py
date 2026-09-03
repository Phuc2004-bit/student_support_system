from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from models.dto.report_dto import SupportReportData
from ui.widgets.dashboard_charts import status_label
from ui.widgets.kpi_card import KpiCard
from ui.widgets.support_filter_widget import (
    SupportFilterSelection,
    SupportFilterWidget,
)


class ReportsPage(QWidget):
    STATE_IDLE = "idle"
    STATE_LOADING = "loading"
    STATE_READY = "ready"
    STATE_EMPTY = "empty"
    STATE_ERROR = "error"

    EMPTY_MESSAGE = "Không có dữ liệu báo cáo phù hợp bộ lọc."

    KPI_TITLES = {
        "total_cases": "Tổng số ca",
        "detected_count": "Mới phát hiện",
        "planned_count": "Đã lập kế hoạch",
        "in_progress_count": "Đang bổ trợ",
        "waiting_review_count": "Chờ đánh giá",
        "continue_count": "Cần tiếp tục",
        "completed_count": "Đã đạt ngưỡng",
    }

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
        "Ngày đánh giá gần nhất",
        "Điểm đánh giá gần nhất",
        "Kết quả đánh giá gần nhất",
    )

    def __init__(
        self,
        academic_service=None,
        report_service=None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.academic_service = academic_service
        self.report_service = report_service
        self.report_data: SupportReportData | None = None
        self._load_state = self.STATE_IDLE
        self.setObjectName("reportsPage")
        self._build_ui()
        self._connect_signals()

    @property
    def load_state(self) -> str:
        return self._load_state

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 24)
        root.setSpacing(16)

        heading = QHBoxLayout()
        titles = QVBoxLayout()
        self.title_label = QLabel("Báo cáo & Thống kê", self)
        self.subtitle_label = QLabel(
            "Tổng hợp tình hình bổ trợ học tập theo ngữ cảnh.",
            self,
        )
        titles.addWidget(self.title_label)
        titles.addWidget(self.subtitle_label)
        heading.addLayout(titles)
        heading.addStretch(1)
        self.refresh_button = QPushButton("Làm mới", self)
        heading.addWidget(self.refresh_button)
        root.addLayout(heading)

        self.filter_widget = SupportFilterWidget(
            academic_service=self.academic_service,
            parent=self,
        )
        root.addWidget(self.filter_widget)
        self.school_year_combo = self.filter_widget.school_year_combo
        self.grade_combo = self.filter_widget.grade_combo
        self.class_combo = self.filter_widget.class_combo
        self.subject_combo = self.filter_widget.subject_combo
        self.status_combo = self.filter_widget.status_combo

        self.state_label = QLabel(self)
        self.state_label.setWordWrap(True)
        root.addWidget(self.state_label)

        self._build_summary_section()
        self._build_cases_section()
        self.charts_frame = self._placeholder_section(
            "reportChartsFrame",
            "Biểu đồ / thống kê",
            "Biểu đồ báo cáo chưa được triển khai.",
        )
        root.addWidget(self.summary_frame)
        root.addWidget(self.cases_frame, 1)
        root.addWidget(self.charts_frame)

        self._show_empty("Vui lòng chọn năm học để tải báo cáo.")

    def _build_summary_section(self) -> None:
        self.summary_frame = QFrame(self)
        self.summary_frame.setObjectName("reportSummaryFrame")
        layout = QVBoxLayout(self.summary_frame)
        self.summary_title_label = QLabel(
            "Tổng quan báo cáo",
            self.summary_frame,
        )
        layout.addWidget(self.summary_title_label)

        grid = QGridLayout()
        grid.setSpacing(12)
        self.kpi_cards: dict[str, KpiCard] = {}
        for index, (key, title) in enumerate(self.KPI_TITLES.items()):
            card = KpiCard(title, self.summary_frame)
            card.setObjectName(f"reportKpiCard_{key}")
            self.kpi_cards[key] = card
            grid.addWidget(card, index // 4, index % 4)
        for column in range(4):
            grid.setColumnStretch(column, 1)
        layout.addLayout(grid)

    def _build_cases_section(self) -> None:
        self.cases_frame = QFrame(self)
        self.cases_frame.setObjectName("reportCasesFrame")
        layout = QVBoxLayout(self.cases_frame)
        self.cases_title_label = QLabel(
            "Danh sách ca bổ trợ",
            self.cases_frame,
        )
        layout.addWidget(self.cases_title_label)

        self.empty_label = QLabel(self.EMPTY_MESSAGE, self.cases_frame)
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.empty_label)

        self.table = QTableWidget(self.cases_frame)
        self.table.setObjectName("reportCasesTable")
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
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table, 1)

    def _placeholder_section(
        self,
        object_name: str,
        title: str,
        message: str,
    ) -> QFrame:
        frame = QFrame(self)
        frame.setObjectName(object_name)
        layout = QVBoxLayout(frame)
        title_label = QLabel(title, frame)
        title_label.setObjectName(f"{object_name}Title")
        message_label = QLabel(message, frame)
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message_label.setWordWrap(True)
        layout.addWidget(title_label)
        layout.addWidget(message_label, 1)
        return frame

    def _connect_signals(self) -> None:
        self.filter_widget.filters_changed.connect(
            self._on_filters_changed
        )
        self.refresh_button.clicked.connect(self.refresh_report)

    def initialize_reports(self) -> bool:
        if self.academic_service is None:
            self._show_empty("Chưa có dữ liệu bộ lọc báo cáo.")
            return False
        try:
            self.filter_widget.load_options()
        except Exception:
            self._show_error()
            return False
        return True

    def current_filters(self) -> SupportFilterSelection:
        return self.filter_widget.current_value()

    def refresh_report(self, *_args) -> bool:
        filters = self.current_filters()
        if filters.school_year_id is None:
            self._show_empty("Vui lòng chọn năm học để tải báo cáo.")
            return False
        if self.report_service is None:
            self._show_empty("Chưa có dịch vụ đọc báo cáo.")
            return False

        self._show_loading()
        try:
            data = self.report_service.get_support_report(
                school_year_id=filters.school_year_id,
                grade_id=filters.grade_id,
                class_id=filters.class_id,
                subject_id=filters.subject_id,
                status=filters.status,
            )
        except Exception:
            self._show_error()
            return False

        self.report_data = data
        self.set_report_data(data)
        if not data.rows:
            self._show_empty(self.EMPTY_MESSAGE, clear_data=False)
            return True

        self._load_state = self.STATE_READY
        self.state_label.setText("Báo cáo đã sẵn sàng.")
        self.refresh_button.setEnabled(True)
        return True

    def set_report_data(self, data: SupportReportData) -> None:
        self.report_data = data
        summary = data.summary
        for key, card in self.kpi_cards.items():
            card.set_value(getattr(summary, key))

        self.table.setRowCount(len(data.rows))
        for row_index, item in enumerate(data.rows):
            values = (
                str(row_index + 1),
                item.student_code,
                item.full_name,
                str(item.grade_number),
                item.class_name,
                item.subject_name,
                str(item.trigger_score),
                item.detected_date.strftime("%d/%m/%Y"),
                status_label(item.status),
                (
                    item.latest_review_date.strftime("%d/%m/%Y")
                    if item.latest_review_date is not None
                    else "-"
                ),
                (
                    str(item.latest_review_score)
                    if item.latest_review_score is not None
                    else "-"
                ),
                self._review_result_label(item.latest_review_result),
            )
            for column, value in enumerate(values):
                table_item = QTableWidgetItem(value)
                if column == 0:
                    table_item.setData(
                        Qt.ItemDataRole.UserRole,
                        item.intervention_id,
                    )
                self.table.setItem(row_index, column, table_item)

        has_rows = bool(data.rows)
        self.empty_label.setVisible(not has_rows)
        self.table.setVisible(has_rows)

    def intervention_id_at_row(self, row: int) -> int | None:
        if row < 0 or row >= self.table.rowCount():
            return None
        item = self.table.item(row, 0)
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    @staticmethod
    def _review_result_label(result: str | None) -> str:
        return {
            "PASSED": "Đạt",
            "NOT_PASSED": "Chưa đạt",
        }.get(result, "-" if result is None else result)

    def _on_filters_changed(
        self,
        _filters: SupportFilterSelection,
    ) -> None:
        self.refresh_report()

    def _show_loading(self) -> None:
        self._load_state = self.STATE_LOADING
        self.state_label.setText("Đang tải báo cáo...")
        self.refresh_button.setEnabled(False)

    def _show_empty(self, message: str, clear_data: bool = True) -> None:
        self._load_state = self.STATE_EMPTY
        if clear_data:
            self.report_data = None
            self._clear_report_display()
        self.state_label.setText(message)
        self.refresh_button.setEnabled(True)

    def _show_error(self) -> None:
        self.report_data = None
        self._clear_report_display()
        self._load_state = self.STATE_ERROR
        self.state_label.setText(
            "Không thể tải báo cáo. Vui lòng thử lại."
        )
        self.refresh_button.setEnabled(True)

    def _clear_report_display(self) -> None:
        for card in self.kpi_cards.values():
            card.set_value(0)
        self.table.setRowCount(0)
        self.table.setVisible(False)
        self.empty_label.setVisible(True)
