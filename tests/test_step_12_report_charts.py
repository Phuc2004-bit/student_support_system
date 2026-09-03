from dataclasses import replace
from datetime import date
from decimal import Decimal
import inspect
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from models.dto.report_dto import (
    SupportReportData,
    SupportReportRow,
    SupportReportSummary,
)
from models.enums import InterventionStatus
from ui.pages.reports_page import ReportsPage
from ui.widgets.dashboard_charts import DashboardBarChart
from tests.test_step_12_report_table_summary import ReportSpy
from tests.test_step_12_reports_page import AcademicStub


def app():
    return QApplication.instance() or QApplication([])


def summary(**changes):
    value = SupportReportSummary(
        total_cases=21,
        detected_count=1,
        planned_count=2,
        in_progress_count=3,
        waiting_review_count=4,
        continue_count=5,
        completed_count=6,
    )
    return replace(value, **changes)


def row(
    intervention_id,
    subject_id,
    subject_code,
    subject_name,
    status="DETECTED",
):
    return SupportReportRow(
        intervention_id=intervention_id,
        student_code=f"HS{intervention_id}",
        full_name=f"Học sinh {intervention_id}",
        grade_number=6,
        class_name="6A1",
        subject_code=subject_code,
        subject_name=subject_name,
        detected_date=date(2026, 10, 1),
        start_date=None,
        status=status,
        trigger_score=Decimal("2.80"),
        subject_id=subject_id,
    )


def data(rows=(), report_summary=None):
    return SupportReportData(report_summary or summary(), tuple(rows))


def heights(chart):
    return [int(patch.get_height()) for patch in chart.axes.patches]


def labels(chart):
    return [item.get_text() for item in chart.axes.get_xticklabels()]


def test_reports_page_contains_two_real_embedded_charts():
    app()
    page = ReportsPage()

    assert page.charts_frame.objectName() == "reportChartsFrame"
    assert isinstance(page.status_chart, DashboardBarChart)
    assert isinstance(page.subject_chart, DashboardBarChart)
    assert page.status_chart.objectName() == "reportStatusChart"
    assert page.subject_chart.objectName() == "reportSubjectChart"
    assert page.status_chart.canvas.parent() is page.status_chart
    assert page.subject_chart.canvas.parent() is page.subject_chart


def test_status_chart_uses_all_six_summary_counts_and_vietnamese_labels():
    app()
    page = ReportsPage()

    page.set_report_data(data())

    assert heights(page.status_chart) == [1, 2, 3, 4, 5, 6]
    assert labels(page.status_chart) == [
        "Mới phát hiện",
        "Đã lập kế hoạch",
        "Đang bổ trợ",
        "Chờ đánh giá",
        "Cần tiếp tục",
        "Đã đạt ngưỡng",
    ]
    assert page.status_chart.axes.get_title() == "Ca bổ trợ theo trạng thái"
    assert page.status_chart.axes.get_ylabel() == "Số ca"


@pytest.mark.parametrize(
    ("field", "position"),
    [
        ("detected_count", 0),
        ("planned_count", 1),
        ("in_progress_count", 2),
        ("waiting_review_count", 3),
        ("continue_count", 4),
        ("completed_count", 5),
    ],
)
def test_each_status_count_comes_from_matching_summary_field(field, position):
    app()
    counts = {name: 0 for _, name in ReportsPage.STATUS_SUMMARY_FIELDS}
    counts[field] = 9
    page = ReportsPage()

    page.set_report_data(data(report_summary=summary(
        total_cases=9,
        **counts,
    )))

    assert heights(page.status_chart)[position] == 9
    assert sum(heights(page.status_chart)) == 9


def test_subject_chart_groups_repeated_rows_by_subject_id():
    app()
    page = ReportsPage()
    rows = (
        row(1, 10, "M10", "Môn Alpha"),
        row(2, 10, "M10", "Môn Alpha"),
        row(3, 20, "M20", "Môn Beta"),
    )

    page.set_report_data(data(rows))

    assert labels(page.subject_chart) == ["Môn Alpha", "Môn Beta"]
    assert heights(page.subject_chart) == [2, 1]
    assert page.subject_chart.axes.get_title() == "Ca bổ trợ theo môn"


def test_subject_chart_uses_identifier_not_presentation_text_for_grouping():
    app()
    page = ReportsPage()
    rows = (
        row(1, 10, "M10", "Cùng tên"),
        row(2, 20, "M20", "Cùng tên"),
    )

    page.set_report_data(data(rows))

    assert labels(page.subject_chart) == ["Cùng tên", "Cùng tên"]
    assert heights(page.subject_chart) == [1, 1]


def test_subject_chart_falls_back_to_code_when_legacy_row_has_no_id():
    app()
    page = ReportsPage()
    rows = (
        row(1, None, "NEW", "Môn mới"),
        row(2, None, "NEW", "Môn mới"),
    )

    page.set_report_data(data(rows))

    assert labels(page.subject_chart) == ["Môn mới"]
    assert heights(page.subject_chart) == [2]


def test_new_subject_appears_without_hard_coded_catalog_values():
    app()
    page = ReportsPage()

    page.set_report_data(data((row(1, 999, "ROBOT", "Robotics"),)))

    assert labels(page.subject_chart) == ["Robotics"]
    assert heights(page.subject_chart) == [1]


def test_one_subject_and_one_positive_status_do_not_crash():
    app()
    one_status = summary(
        total_cases=4,
        detected_count=0,
        planned_count=0,
        in_progress_count=4,
        waiting_review_count=0,
        continue_count=0,
        completed_count=0,
    )
    page = ReportsPage()

    page.set_report_data(data(
        (row(1, 88, "ONE", "Môn duy nhất", "IN_PROGRESS"),),
        one_status,
    ))

    assert sum(heights(page.status_chart)) == 4
    assert heights(page.subject_chart) == [1]


def test_multiple_subjects_are_rendered_in_deterministic_identifier_order():
    app()
    page = ReportsPage()
    rows = (
        row(1, 30, "Z", "Vật lý"),
        row(2, 10, "A", "Âm nhạc"),
        row(3, 20, "B", "Địa lý"),
    )

    page.set_report_data(data(rows))

    assert labels(page.subject_chart) == ["Âm nhạc", "Địa lý", "Vật lý"]
    assert heights(page.subject_chart) == [1, 1, 1]


def test_refresh_renders_kpis_table_and_charts_from_one_service_snapshot():
    app()
    snapshot = data((
        row(1, 10, "A", "Môn A"),
        row(2, 10, "A", "Môn A"),
    ))
    service = ReportSpy(snapshot)
    page = ReportsPage(AcademicStub(), service)

    assert page.initialize_reports() is True

    assert len(service.calls) == 1
    assert page.report_data is snapshot
    assert page.kpi_cards["total_cases"].value == 21
    assert page.table.rowCount() == 2
    assert heights(page.subject_chart) == [2]
    assert heights(page.status_chart) == [1, 2, 3, 4, 5, 6]


def test_filter_refresh_replaces_chart_data_without_extra_service_call():
    app()
    first = data((row(1, 10, "A", "Môn A"),))
    second = data((
        row(2, 20, "B", "Môn B"),
        row(3, 20, "B", "Môn B"),
    ), summary(total_cases=2, detected_count=2))
    service = ReportSpy(first)
    page = ReportsPage(AcademicStub(), service)
    page.initialize_reports()
    service.calls.clear()
    service.data = second

    page.subject_combo.setCurrentIndex(page.subject_combo.findData(11))

    assert len(service.calls) == 1
    assert labels(page.subject_chart) == ["Môn B"]
    assert heights(page.subject_chart) == [2]
    assert heights(page.status_chart)[0] == 2


def test_empty_and_zero_snapshot_clear_both_charts_without_dummy_data():
    app()
    zero = SupportReportSummary(0, 0, 0, 0, 0, 0, 0)
    page = ReportsPage()

    page.set_report_data(data((), zero))

    assert heights(page.status_chart) == []
    assert heights(page.subject_chart) == []
    assert page.status_chart.axes.axison is False
    assert page.subject_chart.axes.axison is False
    assert page.status_chart.axes.texts[0].get_text() == (
        "Không có dữ liệu để hiển thị"
    )


def test_direct_snapshot_refresh_does_not_keep_stale_chart_bars():
    app()
    page = ReportsPage()
    page.set_report_data(data((
        row(1, 10, "A", "Môn A"),
        row(2, 20, "B", "Môn B"),
    )))

    page.set_report_data(data(
        (row(3, 30, "C", "Môn C"),),
        summary(total_cases=1, completed_count=1),
    ))

    assert labels(page.subject_chart) == ["Môn C"]
    assert heights(page.subject_chart) == [1]
    assert heights(page.status_chart)[5] == 1


def test_error_clears_chart_snapshot_and_keeps_page_retryable():
    app()
    service = ReportSpy(data((row(1, 10, "A", "Môn A"),)))
    page = ReportsPage(AcademicStub(), service)
    page.initialize_reports()

    service.fail = True
    assert page.refresh_report() is False

    assert page.load_state == ReportsPage.STATE_ERROR
    assert heights(page.status_chart) == []
    assert heights(page.subject_chart) == []
    assert page.refresh_button.isEnabled()


def test_retry_after_error_renders_fresh_charts():
    app()
    service = ReportSpy(data((row(1, 10, "A", "Môn A"),)))
    page = ReportsPage(AcademicStub(), service)
    page.initialize_reports()
    service.fail = True
    page.refresh_report()
    service.fail = False
    service.data = data((row(2, 20, "B", "Môn B"),))

    assert page.refresh_report() is True

    assert labels(page.subject_chart) == ["Môn B"]
    assert heights(page.subject_chart) == [1]


def test_chart_rendering_is_read_only_and_has_no_data_layer_dependency():
    source = inspect.getsource(
        inspect.getmodule(ReportsPage)
    ).upper()
    for forbidden in (
        "SELECT ",
        "INSERT ",
        "UPDATE ",
        "DELETE ",
        "REPOSITORY",
        "COMMIT",
        "CREATE_SCORE",
        "CREATE_REVIEW",
        "PLAN_INTERVENTION",
        "START_INTERVENTION",
        "REVIEW_INTERVENTION",
    ):
        assert forbidden not in source


def test_chart_render_does_not_call_service_or_mutate_snapshot():
    app()
    rows = (row(1, 10, "A", "Môn A"),)
    snapshot = data(rows)
    service = ReportSpy(snapshot)
    page = ReportsPage(report_service=service)

    page.set_report_data(snapshot)

    assert service.calls == []
    assert snapshot.rows == rows


def test_dashboard_bar_chart_defaults_remain_backward_compatible():
    app()
    chart = DashboardBarChart()

    chart.set_data(ReportsPage._status_chart_items(data()))

    assert chart.objectName() == "dashboardBarChart"
    assert chart.axes.get_title() == "Hồ sơ bổ trợ theo trạng thái"
    assert chart.axes.get_ylabel() == "Số hồ sơ"


def test_reports_page_does_not_integrate_or_export_in_chart_step():
    source = inspect.getsource(
        inspect.getmodule(ReportsPage)
    ).upper()

    assert "EXPORT" not in source
    assert "TOAN" not in source
    assert "VAN" not in source
    assert "MAINWINDOW" not in source
    assert "SEABORN" not in source
