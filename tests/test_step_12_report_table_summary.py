from dataclasses import replace
from datetime import date
from decimal import Decimal
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from models.dto.report_dto import (
    SupportReportData,
    SupportReportRow,
    SupportReportSummary,
)
from models.enums import InterventionStatus
from ui.pages.reports_page import ReportsPage
from ui.widgets.kpi_card import KpiCard
from tests.test_step_12_reports_page import AcademicStub


def app():
    return QApplication.instance() or QApplication([])


def report_summary():
    return SupportReportSummary(
        total_cases=28,
        detected_count=1,
        planned_count=2,
        in_progress_count=3,
        waiting_review_count=4,
        continue_count=5,
        completed_count=13,
    )


def report_row(
    intervention_id=101,
    status="CONTINUE",
    latest_review_date=date(2026, 11, 20),
    latest_review_score=Decimal("3.20"),
    latest_review_result="NOT_PASSED",
):
    return SupportReportRow(
        intervention_id=intervention_id,
        student_code="HS001",
        full_name="Nguyễn Văn A",
        grade_number=6,
        class_name="6A1",
        subject_code="M1",
        subject_name="Môn 1",
        detected_date=date(2026, 10, 10),
        start_date=date(2026, 10, 12),
        status=status,
        trigger_score=Decimal("2.80"),
        latest_review_date=latest_review_date,
        latest_review_score=latest_review_score,
        latest_review_result=latest_review_result,
    )


class ReportSpy:
    def __init__(self, data):
        self.data = data
        self.calls = []
        self.fail = False

    def get_support_report(self, **filters):
        self.calls.append(filters)
        if self.fail:
            raise RuntimeError("raw pyodbc SELECT error")
        return self.data


@pytest.mark.parametrize(
    ("key", "title", "expected"),
    [
        ("total_cases", "Tổng số ca", 28),
        ("detected_count", "Mới phát hiện", 1),
        ("planned_count", "Đã lập kế hoạch", 2),
        ("in_progress_count", "Đang bổ trợ", 3),
        ("waiting_review_count", "Chờ đánh giá", 4),
        ("continue_count", "Cần tiếp tục", 5),
        ("completed_count", "Đã đạt ngưỡng", 13),
    ],
)
def test_summary_cards_render_service_snapshot(key, title, expected):
    app()
    page = ReportsPage()
    page.set_report_data(SupportReportData(
        report_summary(),
        (report_row(),),
    ))

    assert len(page.kpi_cards) == 7
    assert isinstance(page.kpi_cards[key], KpiCard)
    assert page.kpi_cards[key].title == title
    assert page.kpi_cards[key].value == expected


def test_report_table_renders_complete_row_and_preserves_identity():
    app()
    page = ReportsPage()
    page.set_report_data(SupportReportData(
        report_summary(),
        (report_row(),),
    ))

    assert page.table.columnCount() == 12
    assert page.table.rowCount() == 1
    assert page.table.item(0, 0).text() == "1"
    assert page.table.item(0, 1).text() == "HS001"
    assert page.table.item(0, 2).text() == "Nguyễn Văn A"
    assert page.table.item(0, 3).text() == "6"
    assert page.table.item(0, 4).text() == "6A1"
    assert page.table.item(0, 5).text() == "Môn 1"
    assert page.table.item(0, 6).text() == "2.80"
    assert page.table.item(0, 7).text() == "10/10/2026"
    assert page.table.item(0, 8).text() == "Cần tiếp tục"
    assert page.table.item(0, 9).text() == "20/11/2026"
    assert page.table.item(0, 10).text() == "3.20"
    assert page.table.item(0, 11).text() == "Chưa đạt"
    assert page.table.item(0, 0).data(Qt.ItemDataRole.UserRole) == 101
    assert page.intervention_id_at_row(0) == 101


@pytest.mark.parametrize(
    ("status", "display"),
    [
        ("DETECTED", "Mới phát hiện"),
        ("PLANNED", "Đã lập kế hoạch"),
        ("IN_PROGRESS", "Đang bổ trợ"),
        ("WAITING_REVIEW", "Chờ đánh giá"),
        ("CONTINUE", "Cần tiếp tục"),
        ("COMPLETED", "Đã đạt ngưỡng"),
    ],
)
def test_report_table_uses_shared_status_display(status, display):
    app()
    page = ReportsPage()
    page.set_report_data(SupportReportData(
        report_summary(),
        (report_row(status=status),),
    ))

    assert page.table.item(0, 8).text() == display


def test_latest_passed_result_and_missing_review_are_rendered_safely():
    app()
    passed = report_row(
        intervention_id=101,
        latest_review_result="PASSED",
        latest_review_score=Decimal("4.50"),
    )
    no_review = report_row(
        intervention_id=202,
        latest_review_date=None,
        latest_review_score=None,
        latest_review_result=None,
    )
    page = ReportsPage()
    page.set_report_data(SupportReportData(
        report_summary(),
        (passed, no_review),
    ))

    assert page.table.item(0, 10).text() == "4.50"
    assert page.table.item(0, 11).text() == "Đạt"
    assert page.table.item(1, 9).text() == "-"
    assert page.table.item(1, 10).text() == "-"
    assert page.table.item(1, 11).text() == "-"
    assert page.intervention_id_at_row(1) == 202


def test_refresh_renders_summary_and_all_rows_from_one_snapshot_call():
    app()
    data = SupportReportData(
        report_summary(),
        (report_row(101), report_row(202)),
    )
    service = ReportSpy(data)
    page = ReportsPage(AcademicStub(), service)

    assert page.initialize_reports() is True

    assert len(service.calls) == 1
    assert page.report_data is data
    assert page.kpi_cards["total_cases"].value == 28
    assert page.table.rowCount() == 2
    assert page.intervention_id_at_row(0) == 101
    assert page.intervention_id_at_row(1) == 202


def test_empty_snapshot_renders_zero_summary_without_dummy_rows():
    app()
    zero = SupportReportSummary(0, 0, 0, 0, 0, 0, 0)
    page = ReportsPage()

    page.set_report_data(SupportReportData(zero, ()))

    assert all(card.value == 0 for card in page.kpi_cards.values())
    assert page.table.rowCount() == 0
    assert page.table.isHidden()
    assert not page.empty_label.isHidden()


def test_error_clears_stale_snapshot_and_retry_renders_fresh_data():
    app()
    first = SupportReportData(report_summary(), (report_row(),))
    fresh_summary = replace(report_summary(), total_cases=1)
    fresh = SupportReportData(fresh_summary, (report_row(303),))
    service = ReportSpy(first)
    page = ReportsPage(AcademicStub(), service)
    page.initialize_reports()

    service.fail = True
    assert page.refresh_report() is False
    assert page.load_state == ReportsPage.STATE_ERROR
    assert page.report_data is None
    assert all(card.value == 0 for card in page.kpi_cards.values())
    assert page.table.rowCount() == 0
    assert "pyodbc" not in page.state_label.text().lower()

    service.data = fresh
    service.fail = False
    assert page.refresh_report() is True
    assert page.load_state == ReportsPage.STATE_READY
    assert page.kpi_cards["total_cases"].value == 1
    assert page.intervention_id_at_row(0) == 303


def test_filter_refresh_keeps_ids_and_enum_without_extra_row_reads():
    app()
    service = ReportSpy(SupportReportData(
        report_summary(),
        (report_row(),),
    ))
    page = ReportsPage(AcademicStub(), service)
    page.initialize_reports()
    service.calls.clear()

    def select(combo, value):
        combo.setCurrentIndex(combo.findData(value))

    select(page.grade_combo, 6)
    select(page.class_combo, 61)
    select(page.subject_combo, 11)
    select(page.status_combo, InterventionStatus.CONTINUE)
    calls_after_changes = len(service.calls)

    assert service.calls[-1] == {
        "school_year_id": 2,
        "grade_id": 6,
        "class_id": 61,
        "subject_id": 11,
        "status": InterventionStatus.CONTINUE,
    }
    assert calls_after_changes == 4
    assert page.table.rowCount() == 1
