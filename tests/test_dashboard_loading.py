import os
from datetime import date

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from models.dto.dashboard_dto import (
    DashboardData,
    DashboardStatusItem,
    DashboardSummary,
)
from ui.pages.dashboard_page import DashboardPage


def get_app():
    app = QApplication.instance()
    return app or QApplication([])


class FakeAcademicService:
    def list_school_years(self):
        return [
            (
                2,
                "2026-2027",
                date(2026, 9, 1),
                date(2027, 5, 31),
                True,
            )
        ]

    def list_grades(self):
        return [(6, 6, "Khối 6")]

    def list_active_subjects(self):
        return [(1, "TOAN", "Toán")]

    def list_classes_by_school_year(self, school_year_id):
        return [(20, "6A1", 6, None, "ACTIVE")]


class FakeDashboardService:
    def __init__(self):
        self.calls = []

    def get_dashboard(
        self,
        school_year_id,
        grade_id=None,
        class_id=None,
        subject_id=None,
    ):
        self.calls.append(
            (
                school_year_id,
                grade_id,
                class_id,
                subject_id,
            )
        )
        return DashboardData(
            summary=DashboardSummary(
                total_students=1000,
                needs_support_count=120,
                in_progress_count=50,
                waiting_review_count=20,
                completed_count=40,
                continue_count=10,
            ),
            status_breakdown=(
                DashboardStatusItem(
                    status="IN_PROGRESS",
                    count=50,
                ),
            ),
            attention_items=(),
        )


class FailingDashboardService:
    def get_dashboard(self, **kwargs):
        raise RuntimeError("Mất kết nối thử nghiệm")


def test_initialize_loads_filters_and_dashboard_once():
    get_app()
    service = FakeDashboardService()
    page = DashboardPage(
        academic_service=FakeAcademicService(),
        dashboard_service=service,
    )

    page.initialize_dashboard()

    assert len(service.calls) == 1
    assert service.calls[0] == (2, None, None, None)
    assert page.load_state == page.STATE_SUCCESS


def test_successful_refresh_updates_dashboard_data():
    get_app()
    service = FakeDashboardService()
    page = DashboardPage(
        academic_service=FakeAcademicService(),
        dashboard_service=service,
    )
    page.initialize_dashboard()

    assert page.kpi_cards["total_students"].value == 1000
    assert len(page.bar_chart.axes.patches) == 1
    assert page.last_error_message is None


def test_refresh_button_is_connected_to_real_refresh():
    get_app()
    service = FakeDashboardService()
    page = DashboardPage(
        academic_service=FakeAcademicService(),
        dashboard_service=service,
    )
    page.initialize_dashboard()

    before = len(service.calls)
    page.refresh_button.click()

    assert len(service.calls) == before + 1


def test_filter_change_triggers_dashboard_refresh():
    get_app()
    service = FakeDashboardService()
    page = DashboardPage(
        academic_service=FakeAcademicService(),
        dashboard_service=service,
    )
    page.initialize_dashboard()

    before = len(service.calls)
    page.filter_widget.subject_combo.setCurrentIndex(
        page.filter_widget.subject_combo.findData(1)
    )

    assert len(service.calls) == before + 1
    assert service.calls[-1][-1] == 1


def test_dashboard_error_state_is_visible_and_retry_enabled():
    get_app()
    page = DashboardPage(
        academic_service=FakeAcademicService(),
        dashboard_service=FailingDashboardService(),
    )
    page.initialize_dashboard()

    assert page.load_state == page.STATE_ERROR
    assert page.last_error_message == "Mất kết nối thử nghiệm"
    assert "Mất kết nối thử nghiệm" in page.state_label.text()
    assert page.refresh_button.isEnabled() is True
    assert page.filter_widget.isEnabled() is True


def test_page_without_dashboard_service_remains_backward_compatible():
    get_app()
    page = DashboardPage(
        academic_service=FakeAcademicService(),
    )
    page.load_filter_options()

    assert page.refresh_dashboard() is False
    assert page.load_state == page.STATE_IDLE
