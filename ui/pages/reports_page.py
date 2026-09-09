from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from models.dto.dashboard_dto import DashboardStatusItem
from models.dto.report_dto import SupportReportData
from ui.report_excel_actions import ReportExcelActions
from ui.widgets.dashboard_charts import DashboardBarChart
from ui.widgets.kpi_card import KpiCard
from ui.widgets.support_filter_widget import (
    SupportFilterSelection,
    SupportFilterWidget,
)
from utils.report_labels import review_result_label, status_label
from ui.theme import reports_page_stylesheet, status_badge_colors


class ReportsPage(ReportExcelActions, QWidget):
    STATE_IDLE = "idle"
    STATE_LOADING = "loading"
    STATE_READY = "ready"
    STATE_EMPTY = "empty"
    STATE_ERROR = "error"

    EMPTY_MESSAGE = "Không có dữ liệu phù hợp với bộ lọc hiện tại."

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

    STATUS_SUMMARY_FIELDS = (
        ("DETECTED", "detected_count"),
        ("PLANNED", "planned_count"),
        ("IN_PROGRESS", "in_progress_count"),
        ("WAITING_REVIEW", "waiting_review_count"),
        ("CONTINUE", "continue_count"),
        ("COMPLETED", "completed_count"),
    )

    def __init__(
        self,
        academic_service=None,
        report_service=None,
        parent: QWidget | None = None,
        excel_writer=None,
        excel_allowed=None,
    ) -> None:
        super().__init__(parent)
        self.academic_service = academic_service
        self.report_service = report_service
        self._configure_excel_actions(excel_writer, excel_allowed)
        self.report_data: SupportReportData | None = None
        self._report_filters: SupportFilterSelection | None = None
        self._load_state = self.STATE_IDLE
        self.setObjectName("reportsPage")
        self._build_ui()
        self.setStyleSheet(reports_page_stylesheet())
        self._connect_signals()

    @property
    def load_state(self) -> str:
        return self._load_state

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setObjectName("reportsScrollArea")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_contents = QWidget(self.scroll_area)
        self.scroll_contents.setObjectName("reportsScrollContents")
        content = QVBoxLayout(self.scroll_contents)
        content.setContentsMargins(20, 16, 20, 20)
        content.setSpacing(12)

        heading = QHBoxLayout()
        titles = QVBoxLayout()
        self.title_label = QLabel("Báo cáo & Thống kê", self)
        self.subtitle_label = QLabel(
            "Tổng hợp tình hình bổ trợ học tập theo ngữ cảnh.",
            self,
        )
        self.title_label.setObjectName("reportsPageTitle")
        self.subtitle_label.setObjectName("reportsPageSubtitle")
        # The application shell already renders the page heading.
        self.title_label.setVisible(False)
        self.subtitle_label.setVisible(False)
        titles.addWidget(self.title_label)
        titles.addWidget(self.subtitle_label)
        heading.addLayout(titles)
        heading.addStretch(1)
        self.refresh_button = QPushButton("Làm mới", self)
        self.refresh_button.setObjectName("reportsRefreshButton")
        self.refresh_button.setProperty("variant", "primary")
        self._add_excel_action(heading)
        heading.addWidget(self.refresh_button)
        content.addLayout(heading)

        self.filter_frame = QFrame(self.scroll_contents)
        self.filter_frame.setObjectName("reportFilterCard")
        filter_layout = QVBoxLayout(self.filter_frame)
        filter_layout.setContentsMargins(16, 14, 16, 16)
        filter_layout.setSpacing(10)
        self.filter_caption = QLabel("BỘ LỌC BÁO CÁO", self.filter_frame)
        self.filter_caption.setObjectName("reportFilterCaption")
        filter_layout.addWidget(self.filter_caption)
        self.filter_widget = SupportFilterWidget(
            academic_service=self.academic_service,
            parent=self.filter_frame,
        )
        filter_layout.addWidget(self.filter_widget)
        content.addWidget(self.filter_frame)
        self.school_year_combo = self.filter_widget.school_year_combo
        self.grade_combo = self.filter_widget.grade_combo
        self.class_combo = self.filter_widget.class_combo
        self.subject_combo = self.filter_widget.subject_combo
        self.status_combo = self.filter_widget.status_combo

        self.state_label = QLabel(self)
        self.state_label.setObjectName("reportStateLabel")
        self.state_label.setWordWrap(True)
        content.addWidget(self.state_label)

        self._build_summary_section()
        self._build_cases_section()
        self._build_charts_section()
        content.addWidget(self.summary_frame)
        content.addWidget(self.charts_frame)
        content.addWidget(self.cases_frame)
        content.addStretch(1)
        self.scroll_area.setWidget(self.scroll_contents)
        root.addWidget(self.scroll_area)

        self._show_empty("Vui lòng chọn năm học để tải báo cáo.")

    def _build_summary_section(self) -> None:
        self.summary_frame = QFrame(self)
        self.summary_frame.setObjectName("reportSummaryFrame")
        layout = QVBoxLayout(self.summary_frame)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(12)
        self.summary_title_label = QLabel(
            "TỔNG QUAN BÁO CÁO",
            self.summary_frame,
        )
        self.summary_title_label.setObjectName("reportSectionTitle")
        layout.addWidget(self.summary_title_label)

        grid = QGridLayout()
        grid.setSpacing(12)
        self.kpi_cards: dict[str, KpiCard] = {}
        accents = {
            "total_cases": "primary",
            "detected_count": "warning",
            "planned_count": "primary",
            "in_progress_count": "primary",
            "waiting_review_count": "warning",
            "continue_count": "danger",
            "completed_count": "success",
        }
        for index, (key, title) in enumerate(self.KPI_TITLES.items()):
            card = KpiCard(
                title,
                self.summary_frame,
                accent=accents[key],
            )
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
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        cases_header = QHBoxLayout()
        cases_header.setContentsMargins(16, 12, 16, 10)
        self.cases_title_label = QLabel(
            "CHI TIẾT HỒ SƠ BỔ TRỢ",
            self.cases_frame,
        )
        self.cases_title_label.setObjectName("reportSectionTitle")
        cases_header.addWidget(self.cases_title_label)
        cases_header.addStretch(1)
        self.row_count_label = QLabel("0 hồ sơ", self.cases_frame)
        self.row_count_label.setObjectName("reportRowCountLabel")
        cases_header.addWidget(self.row_count_label)
        layout.addLayout(cases_header)

        self.empty_container = QWidget(self.cases_frame)
        empty_layout = QVBoxLayout(self.empty_container)
        empty_layout.setContentsMargins(24, 48, 24, 48)
        self.empty_title_label = QLabel(
            "Chưa có dữ liệu báo cáo", self.empty_container
        )
        self.empty_title_label.setObjectName("reportEmptyTitle")
        self.empty_title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label = QLabel(self.EMPTY_MESSAGE, self.empty_container)
        self.empty_label.setObjectName("reportEmptyDescription")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setWordWrap(True)
        empty_layout.addWidget(self.empty_title_label)
        empty_layout.addWidget(self.empty_label)
        layout.addWidget(self.empty_container)

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
        self.table.setMinimumHeight(280)
        layout.addWidget(self.table, 1)

    def _build_charts_section(self) -> None:
        self.charts_frame = QFrame(self)
        self.charts_frame.setObjectName("reportChartsFrame")
        layout = QVBoxLayout(self.charts_frame)
        layout.setContentsMargins(16, 14, 16, 16)
        layout.setSpacing(12)
        self.charts_title_label = QLabel(
            "BIỂU ĐỒ THỐNG KÊ",
            self.charts_frame,
        )
        self.charts_title_label.setObjectName("reportSectionTitle")
        layout.addWidget(self.charts_title_label)

        charts_layout = QHBoxLayout()
        charts_layout.setSpacing(12)
        self.status_chart = DashboardBarChart(
            self.charts_frame,
            title="Ca bổ trợ theo trạng thái",
            y_label="Số ca",
            empty_message="Không có dữ liệu để hiển thị",
            object_name="reportStatusChart",
        )
        self.subject_chart = DashboardBarChart(
            self.charts_frame,
            title="Ca bổ trợ theo môn",
            y_label="Số ca",
            empty_message="Không có dữ liệu để hiển thị",
            label_formatter=lambda label: label,
            object_name="reportSubjectChart",
        )
        charts_layout.addWidget(self.status_chart, 1)
        charts_layout.addWidget(self.subject_chart, 1)
        layout.addLayout(charts_layout)
        self.charts_frame.setMinimumHeight(330)

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
        self._connect_excel_action()

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
        self._report_filters = filters
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
                review_result_label(item.latest_review_result),
            )
            for column, value in enumerate(values):
                table_item = QTableWidgetItem(value)
                if column == 0:
                    table_item.setData(
                        Qt.ItemDataRole.UserRole,
                        item.intervention_id,
                    )
                if column in (0, 3, 4, 6, 7, 8, 9, 10, 11):
                    table_item.setTextAlignment(
                        Qt.AlignmentFlag.AlignCenter
                    )
                if column == 8:
                    foreground, background = status_badge_colors(
                        item.status
                    )
                    table_item.setForeground(QColor(foreground))
                    table_item.setBackground(QColor(background))
                self.table.setItem(row_index, column, table_item)

        has_rows = bool(data.rows)
        self.empty_container.setVisible(not has_rows)
        self.table.setVisible(has_rows)
        self.row_count_label.setText(f"{len(data.rows)} hồ sơ")
        self.status_chart.set_data(self._status_chart_items(data))
        self.subject_chart.set_data(self._subject_chart_items(data))

    @classmethod
    def _status_chart_items(
        cls,
        data: SupportReportData,
    ) -> tuple[DashboardStatusItem, ...]:
        return tuple(
            DashboardStatusItem(
                status=status,
                count=getattr(data.summary, field_name),
            )
            for status, field_name in cls.STATUS_SUMMARY_FIELDS
        )

    @staticmethod
    def _subject_chart_items(
        data: SupportReportData,
    ) -> tuple[DashboardStatusItem, ...]:
        grouped: dict[tuple[str, object], tuple[str, int]] = {}
        for row in data.rows:
            key = (
                ("id", row.subject_id)
                if row.subject_id is not None
                else ("code", row.subject_code)
            )
            current = grouped.get(key)
            if current is None:
                grouped[key] = (row.subject_name, 1)
            else:
                grouped[key] = (current[0], current[1] + 1)

        ordered = (
            value
            for _, value in sorted(
                grouped.items(),
                key=lambda item: (
                    item[0][0],
                    str(item[0][1]),
                ),
            )
        )
        return tuple(
            DashboardStatusItem(status=str(label), count=int(count))
            for label, count in ordered
        )

    def intervention_id_at_row(self, row: int) -> int | None:
        if row < 0 or row >= self.table.rowCount():
            return None
        item = self.table.item(row, 0)
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

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
            self._report_filters = None
            self._clear_report_display()
        self.state_label.setText(message)
        self.refresh_button.setEnabled(True)

    def _show_error(self) -> None:
        self.report_data = None
        self._report_filters = None
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
        self.empty_container.setVisible(True)
        self.empty_label.setVisible(True)
        self.row_count_label.setText("0 hồ sơ")
        self.status_chart.set_data(())
        self.subject_chart.set_data(())
