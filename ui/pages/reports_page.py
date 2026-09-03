from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from models.dto.report_dto import SupportReportData
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

        self.summary_frame = self._placeholder_section(
            "reportSummaryFrame",
            "Tổng quan báo cáo",
            "Nội dung tổng quan sẽ được triển khai ở bước tiếp theo.",
        )
        self.cases_frame = self._placeholder_section(
            "reportCasesFrame",
            "Danh sách ca bổ trợ",
            "Bảng báo cáo chi tiết chưa được triển khai.",
        )
        self.charts_frame = self._placeholder_section(
            "reportChartsFrame",
            "Biểu đồ / thống kê",
            "Biểu đồ báo cáo chưa được triển khai.",
        )
        root.addWidget(self.summary_frame)
        root.addWidget(self.cases_frame, 1)
        root.addWidget(self.charts_frame)

        self._show_empty("Vui lòng chọn năm học để tải báo cáo.")

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
        if not data.rows:
            self._show_empty(self.EMPTY_MESSAGE, clear_data=False)
            return True

        self._load_state = self.STATE_READY
        self.state_label.setText("Báo cáo đã sẵn sàng.")
        self.refresh_button.setEnabled(True)
        return True

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
        self.state_label.setText(message)
        self.refresh_button.setEnabled(True)

    def _show_error(self) -> None:
        self.report_data = None
        self._load_state = self.STATE_ERROR
        self.state_label.setText(
            "Không thể tải báo cáo. Vui lòng thử lại."
        )
        self.refresh_button.setEnabled(True)
