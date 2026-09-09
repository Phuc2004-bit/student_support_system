from dataclasses import replace
import inspect
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from matplotlib.colors import to_hex
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QScrollArea

from models.dto.report_dto import SupportReportData, SupportReportSummary
from models.enums import InterventionStatus
from ui.pages.reports_page import ReportsPage
from ui.report_excel_actions import ReportExcelActions
from ui.theme import (
    APP_BACKGROUND,
    BORDER,
    SURFACE,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    reports_page_stylesheet,
    status_badge_colors,
)
from tests.test_step_12_report_charts import heights, labels, row
from tests.test_step_12_report_table_summary import ReportSpy
from tests.test_step_12_reports_page import AcademicStub


def app():
    return QApplication.instance() or QApplication([])


def summary(**changes):
    value = SupportReportSummary(6, 1, 1, 1, 1, 1, 1)
    return replace(value, **changes)


def snapshot(rows=(), report_summary=None):
    return SupportReportData(report_summary or summary(), tuple(rows))


def test_reports_page_uses_scrollable_design_system_structure():
    app()
    page = ReportsPage()

    assert isinstance(page.scroll_area, QScrollArea)
    assert page.scroll_area.widget() is page.scroll_contents
    assert page.filter_frame.objectName() == "reportFilterCard"
    assert page.summary_frame.objectName() == "reportSummaryFrame"
    assert page.charts_frame.objectName() == "reportChartsFrame"
    assert page.cases_frame.objectName() == "reportCasesFrame"
    assert page.styleSheet() == reports_page_stylesheet()
    assert APP_BACKGROUND in page.styleSheet()


def test_report_sections_follow_filter_summary_chart_table_order():
    app()
    page = ReportsPage()
    layout = page.scroll_contents.layout()

    assert layout.indexOf(page.filter_frame) < layout.indexOf(page.summary_frame)
    assert layout.indexOf(page.summary_frame) < layout.indexOf(page.charts_frame)
    assert layout.indexOf(page.charts_frame) < layout.indexOf(page.cases_frame)
    assert page.title_label.isHidden()
    assert page.subtitle_label.isHidden()


def test_report_filters_keep_five_existing_controls_and_status_values():
    app()
    page = ReportsPage()

    assert all(
        combo is not None
        for combo in (
            page.school_year_combo,
            page.grade_combo,
            page.class_combo,
            page.subject_combo,
            page.status_combo,
        )
    )
    assert [
        page.status_combo.itemData(index)
        for index in range(1, page.status_combo.count())
    ] == list(InterventionStatus)


def test_summary_cards_render_exact_snapshot_with_semantic_accents():
    app()
    page = ReportsPage()
    data = snapshot(report_summary=summary(
        total_cases=18,
        detected_count=2,
        planned_count=3,
        in_progress_count=4,
        waiting_review_count=1,
        continue_count=2,
        completed_count=6,
    ))

    page.set_report_data(data)

    assert page.kpi_cards["total_cases"].value == 18
    assert page.kpi_cards["continue_count"].value == 2
    assert page.kpi_cards["completed_count"].value == 6
    assert page.kpi_cards["continue_count"].property("accent") == "danger"
    assert page.kpi_cards["completed_count"].property("accent") == "success"


def test_both_report_charts_are_fully_dark_and_readable():
    app()
    page = ReportsPage()
    page.set_report_data(snapshot((
        row(1, 10, "M10", "Môn Alpha", "DETECTED"),
        row(2, 20, "M20", "Môn Beta", "COMPLETED"),
    )))

    for chart in (page.status_chart, page.subject_chart):
        assert to_hex(chart.figure.get_facecolor()).upper() == SURFACE
        assert to_hex(chart.axes.get_facecolor()).upper() == SURFACE
        assert SURFACE in chart.canvas.styleSheet()
        assert chart.axes.title.get_color() == TEXT_PRIMARY
        assert chart.axes.yaxis.label.get_color() == TEXT_SECONDARY
        assert all(
            to_hex(spine.get_edgecolor()).upper() == BORDER
            for spine in chart.axes.spines.values()
        )


def test_chart_empty_state_is_dark_centered_and_has_no_bars():
    app()
    page = ReportsPage()
    zero = SupportReportSummary(0, 0, 0, 0, 0, 0, 0)

    page.set_report_data(snapshot((), zero))

    for chart in (page.status_chart, page.subject_chart):
        assert heights(chart) == []
        assert chart.axes.axison is False
        assert chart.axes.texts[0].get_text() == "Không có dữ liệu để hiển thị"
        assert to_hex(chart.figure.get_facecolor()).upper() == SURFACE


def test_status_chart_keeps_all_six_categories_and_vietnamese_mapping():
    app()
    page = ReportsPage()

    page.set_report_data(snapshot())

    assert heights(page.status_chart) == [1, 1, 1, 1, 1, 1]
    assert labels(page.status_chart) == [
        "Mới phát hiện",
        "Đã lập kế hoạch",
        "Đang bổ trợ",
        "Chờ đánh giá",
        "Cần tiếp tục",
        "Đã đạt ngưỡng",
    ]


def test_report_table_is_compact_dark_and_uses_text_status_badge():
    app()
    page = ReportsPage()
    data = snapshot((row(1, 10, "M10", "Môn Alpha", "CONTINUE"),))

    page.set_report_data(data)

    status_item = page.table.item(0, 8)
    foreground, background = status_badge_colors("CONTINUE")
    assert page.table.rowCount() == 1
    assert page.table.columnCount() == len(page.TABLE_HEADERS)
    assert page.table.verticalHeader().defaultSectionSize() == 40
    assert page.table.showGrid() is False
    assert page.table.horizontalHeader().sectionResizeMode(2) == (
        page.table.horizontalHeader().ResizeMode.Stretch
    )
    assert status_item.text() == "Cần tiếp tục"
    assert status_item.foreground().color().name().upper() == foreground
    assert status_item.background().color().name().upper() == background
    assert status_item.textAlignment() == int(Qt.AlignmentFlag.AlignCenter)


def test_table_empty_state_and_row_counter_are_explicit():
    app()
    page = ReportsPage()
    zero = SupportReportSummary(0, 0, 0, 0, 0, 0, 0)

    page.set_report_data(snapshot((), zero))

    assert page.empty_container.isHidden() is False
    assert page.empty_label.text() == page.EMPTY_MESSAGE
    assert page.table.isHidden()
    assert page.row_count_label.text() == "0 hồ sơ"


def test_status_filter_summary_table_and_chart_use_same_service_snapshot():
    app()
    completed_row = row(1, 10, "M10", "Môn Alpha", "COMPLETED")
    completed = snapshot(
        (completed_row,),
        summary(
            total_cases=1,
            detected_count=0,
            planned_count=0,
            in_progress_count=0,
            waiting_review_count=0,
            continue_count=0,
            completed_count=1,
        ),
    )
    service = ReportSpy(completed)
    page = ReportsPage(AcademicStub(), service)
    page.initialize_reports()
    service.calls.clear()

    page.status_combo.setCurrentIndex(
        page.status_combo.findData(InterventionStatus.COMPLETED)
    )

    assert service.calls[-1]["status"] == InterventionStatus.COMPLETED
    assert page.kpi_cards["total_cases"].value == 1
    assert page.table.rowCount() == 1
    assert page.table.item(0, 8).text() == "Đã đạt ngưỡng"
    assert heights(page.status_chart) == [0, 0, 0, 0, 0, 1]
    assert heights(page.subject_chart) == [1]


def test_export_action_is_secondary_and_permission_guard_is_unchanged():
    app()
    denied = ReportsPage(excel_allowed=lambda: False)
    allowed = ReportsPage(excel_allowed=lambda: True)

    assert denied.export_button.isHidden()
    assert not denied.export_button.isEnabled()
    assert not allowed.export_button.isHidden()
    assert allowed.export_button.isEnabled()
    assert allowed.export_button.property("variant") == "secondary"
    assert allowed.refresh_button.property("variant") == "primary"


def test_responsive_construction_uses_layouts_and_scroll_at_target_sizes():
    app()
    page = ReportsPage()

    for width, height in ((1366, 768), (1920, 1080)):
        page.resize(width, height)
        page.show()
        app().processEvents()
        assert page.scroll_area.viewport().width() > 0
        assert page.scroll_area.viewport().height() > 0
        assert page.scroll_area.widgetResizable()
    page.close()


def test_reports_presentation_has_no_data_or_business_layer_logic():
    modules = (
        inspect.getmodule(ReportsPage),
        inspect.getmodule(ReportExcelActions),
    )
    source = "\n".join(inspect.getsource(module) for module in modules).upper()

    for forbidden in (
        "SELECT ",
        "INSERT ",
        "UPDATE ",
        "DELETE ",
        "REPOSITORY",
        ".COMMIT(",
        ".ROLLBACK(",
        "CREATE_SCORE",
        "REVIEW_INTERVENTION",
    ):
        assert forbidden not in source
    assert "GIÚP HỌC SINH TIẾN BỘ" not in source
    assert "NHỜ HỆ THỐNG" not in source
