from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from models.dto.dashboard_dto import DashboardData, DashboardSummary
from services.academic_service import AcademicService
from services.dashboard_contract import DashboardServiceContract
from ui.widgets.dashboard_filter import DashboardFilterWidget
from ui.widgets.dashboard_charts import DashboardBarChart, DashboardDonutChart
from ui.widgets.dashboard_attention import DashboardAttentionTable
from ui.widgets.kpi_card import KpiCard


class DashboardPage(QWidget):
    TITLE = "Tổng quan"

    KPI_DEFINITIONS = (
        ("total_students", "Tổng học sinh", "primary"),
        ("needs_support_count", "Cần bổ trợ", "warning"),
        ("in_progress_count", "Đang bổ trợ", "primary"),
        ("completed_count", "Đã đạt ngưỡng", "success"),
        ("waiting_review_count", "Chờ đánh giá", "warning"),
        ("continue_count", "Cần tiếp tục", "danger"),
    )

    STATE_IDLE = "IDLE"
    STATE_LOADING = "LOADING"
    STATE_SUCCESS = "SUCCESS"
    STATE_ERROR = "ERROR"

    def __init__(
        self,
        academic_service: AcademicService | None = None,
        dashboard_service: DashboardServiceContract | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.academic_service = academic_service
        self.dashboard_service = dashboard_service
        self._load_state = self.STATE_IDLE
        self._last_error_message: str | None = None

        self.setObjectName("dashboardPage")
        self.kpi_cards: dict[str, KpiCard] = {}

        self._build_ui()
        self._connect_dashboard_signals()

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setObjectName("dashboardScrollArea")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        self.scroll_contents = QWidget(self.scroll_area)
        self.scroll_contents.setObjectName("dashboardScrollContents")
        content_layout = QVBoxLayout(self.scroll_contents)
        content_layout.setContentsMargins(24, 20, 24, 24)
        content_layout.setSpacing(16)

        self._build_header(content_layout)
        self._build_kpi_section(content_layout)
        self._build_filter_section(content_layout)
        self._build_chart_section(content_layout)
        self._build_attention_section(content_layout)
        content_layout.addStretch(1)

        self.scroll_area.setWidget(self.scroll_contents)
        root_layout.addWidget(self.scroll_area)

    def _build_header(self, parent_layout: QVBoxLayout) -> None:
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        title_container = QVBoxLayout()
        title_container.setSpacing(4)

        self.title_label = QLabel(self.TITLE, self)
        self.title_label.setObjectName("dashboardTitleLabel")

        self.subtitle_label = QLabel(
            "Theo dõi tình hình học sinh cần bổ trợ học tập",
            self,
        )
        self.subtitle_label.setObjectName("dashboardSubtitleLabel")

        self.state_label = QLabel("", self)
        self.state_label.setObjectName("dashboardStateLabel")
        self.state_label.setVisible(False)

        title_container.addWidget(self.title_label)
        title_container.addWidget(self.subtitle_label)
        title_container.addWidget(self.state_label)

        header_layout.addLayout(title_container)
        header_layout.addStretch(1)

        self.refresh_button = QPushButton("Làm mới", self)
        self.refresh_button.setObjectName("dashboardRefreshButton")
        self.refresh_button.setProperty("variant", "primary")
        self.refresh_button.setCursor(Qt.CursorShape.PointingHandCursor)
        header_layout.addWidget(
            self.refresh_button,
            alignment=Qt.AlignmentFlag.AlignTop,
        )

        parent_layout.addLayout(header_layout)

    @property
    def load_state(self) -> str:
        return self._load_state

    @property
    def last_error_message(self) -> str | None:
        return self._last_error_message

    def _connect_dashboard_signals(self) -> None:
        self.refresh_button.clicked.connect(
            self.refresh_dashboard
        )

        if self.filter_widget is not None:
            self.filter_widget.filters_changed.connect(
                self._on_filters_changed
            )

    def _build_filter_section(self, parent_layout: QVBoxLayout) -> None:
        self.filter_frame = self._create_section_frame(
            "dashboardFilterFrame"
        )

        layout = QVBoxLayout(self.filter_frame)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        self.filter_title_label = QLabel(
            "Bộ lọc",
            self.filter_frame,
        )
        self.filter_title_label.setObjectName(
            "dashboardFilterTitleLabel"
        )
        layout.addWidget(self.filter_title_label)

        self.filter_widget: DashboardFilterWidget | None = None

        if self.academic_service is not None:
            self.filter_widget = DashboardFilterWidget(
                self.academic_service,
                self.filter_frame,
            )
            layout.addWidget(self.filter_widget)
        else:
            # Giữ tương thích với MainWindow hiện tại.
            # Service sẽ được nối ở bước integration tiếp theo.
            self.filter_placeholder_label = QLabel(
                "Năm học • Khối • Lớp • Môn",
                self.filter_frame,
            )
            self.filter_placeholder_label.setObjectName(
                "dashboardFilterPlaceholderLabel"
            )
            layout.addWidget(self.filter_placeholder_label)

        parent_layout.addWidget(self.filter_frame)

    def _build_kpi_section(self, parent_layout: QVBoxLayout) -> None:
        self.kpi_frame = self._create_section_frame(
            "dashboardKpiFrame"
        )

        section_layout = QVBoxLayout(self.kpi_frame)
        section_layout.setContentsMargins(16, 12, 16, 16)
        section_layout.setSpacing(12)

        self.kpi_title_label = QLabel(
            "Chỉ số tổng quan",
            self.kpi_frame,
        )
        self.kpi_title_label.setObjectName("dashboardKpiTitleLabel")
        section_layout.addWidget(self.kpi_title_label)

        self.kpi_grid_layout = QGridLayout()
        self.kpi_grid_layout.setHorizontalSpacing(12)
        self.kpi_grid_layout.setVerticalSpacing(12)

        for index, (key, title, accent) in enumerate(self.KPI_DEFINITIONS):
            card = KpiCard(
                title=title,
                parent=self.kpi_frame,
                accent=accent,
            )
            card.setObjectName(f"kpiCard_{key}")
            self.kpi_cards[key] = card

            self.kpi_grid_layout.addWidget(
                card,
                index // 4,
                index % 4,
            )

        for column in range(4):
            self.kpi_grid_layout.setColumnStretch(column, 1)

        section_layout.addLayout(self.kpi_grid_layout)
        parent_layout.addWidget(self.kpi_frame)

    def _build_chart_section(self, parent_layout: QVBoxLayout) -> None:
        self.chart_frame = self._create_section_frame(
            "dashboardChartFrame"
        )
        layout = QVBoxLayout(self.chart_frame)
        layout.setContentsMargins(16, 12, 16, 16)
        layout.setSpacing(12)

        self.chart_title_label = QLabel("Biểu đồ", self.chart_frame)
        self.chart_title_label.setObjectName("dashboardChartTitleLabel")
        layout.addWidget(self.chart_title_label)

        charts_layout = QHBoxLayout()
        charts_layout.setSpacing(12)

        self.bar_chart = DashboardBarChart(self.chart_frame)
        self.donut_chart = DashboardDonutChart(self.chart_frame)
        self.bar_chart.setMinimumHeight(290)
        self.donut_chart.setMinimumHeight(290)

        charts_layout.addWidget(self.bar_chart, 1)
        charts_layout.addWidget(self.donut_chart, 1)

        layout.addLayout(charts_layout)
        parent_layout.addWidget(self.chart_frame)

    def _build_attention_section(self, parent_layout: QVBoxLayout) -> None:
        self.attention_frame = self._create_section_frame(
            "dashboardAttentionFrame"
        )
        layout = QVBoxLayout(self.attention_frame)
        layout.setContentsMargins(16, 12, 16, 16)
        layout.setSpacing(10)

        self.attention_title_label = QLabel(
            "Học sinh cần chú ý",
            self.attention_frame,
        )
        self.attention_title_label.setObjectName(
            "dashboardAttentionTitleLabel"
        )

        self.attention_table = DashboardAttentionTable(
            self.attention_frame
        )

        layout.addWidget(self.attention_title_label)
        layout.addWidget(self.attention_table)
        parent_layout.addWidget(self.attention_frame)

    def set_summary(self, summary: DashboardSummary) -> None:
        if summary is None:
            raise ValueError(
                "DashboardSummary không được để trống."
            )

        values = {
            "total_students": summary.total_students,
            "needs_support_count": summary.needs_support_count,
            "in_progress_count": summary.in_progress_count,
            "waiting_review_count": summary.waiting_review_count,
            "completed_count": summary.completed_count,
            "continue_count": summary.continue_count,
        }

        for key, value in values.items():
            self.kpi_cards[key].set_value(value)

    def set_dashboard_data(self, data: DashboardData) -> None:
        if data is None:
            raise ValueError(
                "DashboardData không được để trống."
            )

        self.set_summary(data.summary)
        self.set_status_breakdown(data.status_breakdown)
        self.set_attention_items(data.attention_items)

    def set_status_breakdown(self, items) -> None:
        data = tuple(items)
        self.bar_chart.set_data(data)
        self.donut_chart.set_data(data)

    def set_attention_items(self, items) -> None:
        self.attention_table.set_items(items)

    def load_filter_options(self) -> None:
        if self.filter_widget is not None:
            self.filter_widget.load_options()

    def initialize_dashboard(self) -> None:
        """
        Nạp danh mục bộ lọc và Dashboard lần đầu.

        Khi có DashboardFilterWidget, load_options() sẽ phát
        filters_changed và tự kích hoạt refresh_dashboard().
        """
        if self.filter_widget is not None:
            self.load_filter_options()
            return

        self.refresh_dashboard()

    def refresh_dashboard(self) -> bool:
        """
        Tải lại Dashboard theo bộ lọc hiện tại.

        Trả về True khi tải thành công, False khi chưa đủ dependency,
        chưa có năm học hoặc khi Service phát sinh lỗi.
        """
        if self.dashboard_service is None:
            return False

        if self.filter_widget is None:
            return False

        filters = self.filter_widget.current_value()

        if filters.school_year_id is None:
            self._set_error_state(
                "Chưa có năm học để hiển thị Dashboard."
            )
            return False

        self._set_loading_state()

        try:
            data = self.dashboard_service.get_dashboard(
                school_year_id=filters.school_year_id,
                grade_id=filters.grade_id,
                class_id=filters.class_id,
                subject_id=filters.subject_id,
            )
        except Exception as exc:
            self._set_error_state(str(exc))
            return False

        self.set_dashboard_data(data)
        self._set_success_state()
        return True

    def _on_filters_changed(self, _filters) -> None:
        if self.dashboard_service is not None:
            self.refresh_dashboard()

    def _set_loading_state(self) -> None:
        self._load_state = self.STATE_LOADING
        self._last_error_message = None

        self.state_label.setText("Đang tải dữ liệu...")
        self.state_label.setVisible(True)
        self.refresh_button.setEnabled(False)

        if self.filter_widget is not None:
            self.filter_widget.setEnabled(False)

    def _set_success_state(self) -> None:
        self._load_state = self.STATE_SUCCESS
        self._last_error_message = None

        self.state_label.clear()
        self.state_label.setVisible(False)
        self.refresh_button.setEnabled(True)

        if self.filter_widget is not None:
            self.filter_widget.setEnabled(True)

    def _set_error_state(self, message: str) -> None:
        normalized = (
            str(message).strip()
            if message is not None
            else ""
        )
        if not normalized:
            normalized = "Không thể tải dữ liệu Dashboard."

        self._load_state = self.STATE_ERROR
        self._last_error_message = normalized

        self.state_label.setText(
            f"Lỗi tải dữ liệu: {normalized}"
        )
        self.state_label.setVisible(True)
        self.refresh_button.setEnabled(True)

        if self.filter_widget is not None:
            self.filter_widget.setEnabled(True)

    @staticmethod
    def _create_section_frame(object_name: str) -> QFrame:
        frame = QFrame()
        frame.setObjectName(object_name)
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        return frame
