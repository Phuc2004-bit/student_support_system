from datetime import date
from decimal import Decimal
import inspect
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QComboBox

from app_context import AppContext
from models.dto import UserSession
from models.dto.report_dto import (
    SupportReportData,
    SupportReportRow,
    SupportReportSummary,
)
from models.enums import InterventionStatus, UserRole
from services.permission_service import PermissionService
from ui.main_window import MainWindow
from ui.pages.placeholder_page import PlaceholderPage
from ui.pages.reports_page import ReportsPage
from ui.widgets.support_filter_widget import SupportFilterWidget


def app():
    return QApplication.instance() or QApplication([])


class AcademicStub:
    def __init__(self):
        self.year_calls = 0
        self.grade_calls = 0
        self.class_calls = []
        self.subject_calls = 0

    def list_school_years(self):
        self.year_calls += 1
        return [
            (1, "2025-2026", None, None, False),
            (2, "2026-2027", None, None, True),
        ]

    def list_grades(self):
        self.grade_calls += 1
        return [(6, 6, "Khối 6"), (7, 7, "Khối 7")]

    def list_classes_by_school_year(self, year_id):
        self.class_calls.append(year_id)
        return {
            1: [(51, "6B1", 6, None, True)],
            2: [
                (61, "6A1", 6, None, True),
                (62, "6A2", 6, None, True),
                (71, "7A1", 7, None, True),
                (72, "7OLD", 7, None, False),
            ],
        }.get(year_id, [])

    def list_active_subjects(self):
        self.subject_calls += 1
        return [(11, "M1", "Môn 1"), (12, "M2", "Môn 2")]


def summary(total=1):
    return SupportReportSummary(total, 1, 0, 0, 0, 0, 0)


def row():
    return SupportReportRow(
        101,
        "HS001",
        "Học sinh A",
        6,
        "6A1",
        "M1",
        "Môn 1",
        date(2026, 10, 1),
        None,
        "DETECTED",
        Decimal("2.80"),
    )


class ReportStub:
    def __init__(self, data=None):
        self.data = data or SupportReportData(summary(), (row(),))
        self.calls = []
        self.fail = False

    def get_support_report(self, **filters):
        assert page_under_load.load_state == ReportsPage.STATE_LOADING
        assert not page_under_load.refresh_button.isEnabled()
        self.calls.append(filters)
        if self.fail:
            raise RuntimeError("raw pyodbc SELECT failure")
        return self.data


page_under_load = None


def select(combo, value):
    index = combo.findData(value)
    assert index >= 0
    combo.setCurrentIndex(index)


def test_reports_page_builds_shell_and_reuses_five_filter_widget():
    app()
    page = ReportsPage()

    assert page.title_label.text() == "Báo cáo & Thống kê"
    assert isinstance(page.filter_widget, SupportFilterWidget)
    assert all(isinstance(control, QComboBox) for control in (
        page.school_year_combo,
        page.grade_combo,
        page.class_combo,
        page.subject_combo,
        page.status_combo,
    ))
    assert page.summary_frame.objectName() == "reportSummaryFrame"
    assert page.cases_frame.objectName() == "reportCasesFrame"
    assert page.charts_frame.objectName() == "reportChartsFrame"


def test_initialize_loads_years_grades_subjects_classes_and_statuses():
    global page_under_load
    app()
    academic = AcademicStub()
    report = ReportStub()
    page_under_load = ReportsPage(academic, report)

    assert page_under_load.initialize_reports() is True
    assert academic.year_calls == 1
    assert academic.grade_calls == 1
    assert academic.class_calls == [2]
    assert academic.subject_calls == 1
    assert page_under_load.school_year_combo.currentData() == 2
    assert [
        page_under_load.status_combo.itemData(index)
        for index in range(1, page_under_load.status_combo.count())
    ] == list(InterventionStatus)
    assert len(report.calls) == 1
    assert page_under_load.load_state == ReportsPage.STATE_READY


def test_year_change_resets_grade_and_reloads_classes():
    global page_under_load
    app()
    academic = AcademicStub()
    page_under_load = ReportsPage(academic, ReportStub())
    page_under_load.initialize_reports()
    select(page_under_load.grade_combo, 7)
    select(page_under_load.class_combo, 71)

    select(page_under_load.school_year_combo, 1)

    assert academic.class_calls[-1] == 1
    assert page_under_load.grade_combo.currentData() is None
    assert page_under_load.class_combo.currentData() is None
    assert page_under_load.class_combo.findData(51) >= 0


def test_grade_filters_active_classes():
    global page_under_load
    app()
    page_under_load = ReportsPage(AcademicStub(), ReportStub())
    page_under_load.initialize_reports()

    select(page_under_load.grade_combo, 7)

    assert page_under_load.class_combo.findData(71) >= 0
    assert page_under_load.class_combo.findData(61) == -1
    assert page_under_load.class_combo.findData(72) == -1


def test_filter_ids_and_status_reach_one_report_snapshot_call():
    global page_under_load
    app()
    report = ReportStub()
    page_under_load = ReportsPage(AcademicStub(), report)
    page_under_load.initialize_reports()
    select(page_under_load.grade_combo, 6)
    select(page_under_load.class_combo, 61)
    select(page_under_load.subject_combo, 11)
    select(page_under_load.status_combo, InterventionStatus.DETECTED)

    assert report.calls[-1] == {
        "school_year_id": 2,
        "grade_id": 6,
        "class_id": 61,
        "subject_id": 11,
        "status": InterventionStatus.DETECTED,
    }


def test_empty_report_has_safe_empty_state():
    global page_under_load
    app()
    report = ReportStub(SupportReportData(summary(0), ()))
    page_under_load = ReportsPage(AcademicStub(), report)

    assert page_under_load.initialize_reports() is True
    assert page_under_load.load_state == ReportsPage.STATE_EMPTY
    assert page_under_load.report_data.rows == ()
    assert page_under_load.state_label.text() == ReportsPage.EMPTY_MESSAGE


def test_error_is_normalized_and_page_can_retry():
    global page_under_load
    app()
    report = ReportStub()
    report.fail = True
    page_under_load = ReportsPage(AcademicStub(), report)

    assert page_under_load.initialize_reports() is True
    assert page_under_load.load_state == ReportsPage.STATE_ERROR
    assert "pyodbc" not in page_under_load.state_label.text().lower()
    assert "select" not in page_under_load.state_label.text().lower()
    assert page_under_load.refresh_button.isEnabled()

    report.fail = False
    assert page_under_load.refresh_report() is True
    assert page_under_load.load_state == ReportsPage.STATE_READY


def test_missing_or_empty_dependencies_do_not_crash():
    app()

    class EmptyAcademic(AcademicStub):
        def list_school_years(self):
            return []

        def list_grades(self):
            return []

        def list_active_subjects(self):
            return []

    no_service = ReportsPage()
    empty = ReportsPage(EmptyAcademic(), ReportStub())

    assert no_service.initialize_reports() is False
    assert empty.initialize_reports() is True
    assert empty.school_year_combo.currentData() is None
    assert empty.load_state == ReportsPage.STATE_EMPTY


def test_reports_ui_is_read_only_and_has_no_data_layer_dependencies():
    source = inspect.getsource(
        inspect.getmodule(ReportsPage)
    ).upper()
    for forbidden in (
        "SELECT ",
        "INSERT ",
        "UPDATE ",
        "DELETE ",
        "REPOSITORY",
        "PLAN_INTERVENTION",
        "START_INTERVENTION",
        "MARK_WAITING_REVIEW",
        "CONTINUE_INTERVENTION",
        "REVIEW_INTERVENTION",
        "CREATE_SCORE",
        "CREATE_REVIEW",
        "COMMIT",
    ):
        assert forbidden not in source


def test_reports_page_is_not_integrated_into_main_window_yet():
    app()
    context = AppContext(
        db=object(),
        auth_service=object(),
        permission_service=PermissionService(),
        session=UserSession(1, "admin", "Admin", UserRole.ADMIN),
    )

    window = MainWindow(context)

    assert isinstance(window.pages["reports"], PlaceholderPage)
