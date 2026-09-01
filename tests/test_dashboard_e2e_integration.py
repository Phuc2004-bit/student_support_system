import os
from datetime import date
from decimal import Decimal

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from models.dto.dashboard_dto import (
    DashboardAttentionItem,
    DashboardData,
    DashboardStatusItem,
    DashboardSummary,
)
from ui.pages.dashboard_page import DashboardPage


def get_app():
    app = QApplication.instance()
    return app or QApplication([])


class AcademicServiceStub:
    def list_school_years(self):
        return [
            (
                1,
                "2025-2026",
                date(2025, 9, 1),
                date(2026, 5, 31),
                False,
            ),
            (
                2,
                "2026-2027",
                date(2026, 9, 1),
                date(2027, 5, 31),
                True,
            ),
        ]

    def list_grades(self):
        return [
            (6, 6, "Khối 6"),
            (7, 7, "Khối 7"),
        ]

    def list_active_subjects(self):
        return [
            (1, "TOAN", "Toán"),
            (2, "VAN", "Ngữ văn"),
        ]

    def list_classes_by_school_year(self, school_year_id):
        if school_year_id == 2:
            return [
                (20, "6A1", 6, None, "ACTIVE"),
                (21, "7A1", 7, None, "ACTIVE"),
            ]
        return []


def make_data(
    total_students=1000,
    needs_support=120,
    status="WAITING_REVIEW",
):
    return DashboardData(
        summary=DashboardSummary(
            total_students=total_students,
            needs_support_count=needs_support,
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
            DashboardStatusItem(
                status="WAITING_REVIEW",
                count=20,
            ),
        ),
        attention_items=(
            DashboardAttentionItem(
                intervention_id=501,
                student_code="HS0001",
                full_name="Nguyễn Văn A",
                grade_number=6,
                class_name="6A1",
                subject_code="TOAN",
                subject_name="Toán",
                status=status,
                detected_date=date(2026, 9, 15),
                trigger_score=Decimal("2.80"),
                latest_review_score=Decimal("3.20"),
            ),
        ),
    )


class DashboardServiceStub:
    def __init__(self, data=None):
        self.data = data or make_data()
        self.calls = []
        self.error = None

    def get_dashboard(
        self,
        school_year_id,
        grade_id=None,
        class_id=None,
        subject_id=None,
    ):
        self.calls.append(
            {
                "school_year_id": school_year_id,
                "grade_id": grade_id,
                "class_id": class_id,
                "subject_id": subject_id,
            }
        )

        if self.error is not None:
            raise self.error

        return self.data


def build_page():
    service = DashboardServiceStub()
    page = DashboardPage(
        academic_service=AcademicServiceStub(),
        dashboard_service=service,
    )
    return page, service


def test_dashboard_initialization_populates_all_regions():
    get_app()
    page, service = build_page()

    page.initialize_dashboard()

    assert len(service.calls) == 1
    assert service.calls[0]["school_year_id"] == 2

    assert page.kpi_cards["total_students"].value == 1000
    assert page.kpi_cards["needs_support_count"].value == 120

    assert len(page.bar_chart.axes.patches) == 2
    assert page.attention_table.table.rowCount() == 1
    assert (
        page.attention_table.table.item(0, 0).text()
        == "HS0001"
    )
    assert page.load_state == page.STATE_SUCCESS


def test_subject_filter_reaches_dashboard_service():
    get_app()
    page, service = build_page()
    page.initialize_dashboard()

    index = page.filter_widget.subject_combo.findData(1)
    page.filter_widget.subject_combo.setCurrentIndex(index)

    assert service.calls[-1]["school_year_id"] == 2
    assert service.calls[-1]["subject_id"] == 1


def test_grade_filter_reaches_dashboard_service():
    get_app()
    page, service = build_page()
    page.initialize_dashboard()

    index = page.filter_widget.grade_combo.findData(6)
    page.filter_widget.grade_combo.setCurrentIndex(index)

    assert service.calls[-1]["grade_id"] == 6


def test_manual_refresh_replaces_all_dashboard_content():
    get_app()
    page, service = build_page()
    page.initialize_dashboard()

    service.data = make_data(
        total_students=980,
        needs_support=90,
        status="CONTINUE",
    )

    page.refresh_button.click()

    assert page.kpi_cards["total_students"].value == 980
    assert page.kpi_cards["needs_support_count"].value == 90
    assert (
        page.attention_table.table.item(0, 4).text()
        == "Cần tiếp tục"
    )


def test_failed_refresh_preserves_last_successful_dashboard_data():
    get_app()
    page, service = build_page()
    page.initialize_dashboard()

    assert page.kpi_cards["total_students"].value == 1000

    service.error = RuntimeError("SQL Server tạm thời không khả dụng")
    result = page.refresh_dashboard()

    assert result is False
    assert page.load_state == page.STATE_ERROR
    assert page.kpi_cards["total_students"].value == 1000
    assert page.attention_table.table.rowCount() == 1


def test_dashboard_can_recover_after_error():
    get_app()
    page, service = build_page()
    page.initialize_dashboard()

    service.error = RuntimeError("Lỗi thử nghiệm")
    assert page.refresh_dashboard() is False

    service.error = None
    service.data = make_data(
        total_students=995,
        needs_support=100,
    )

    assert page.refresh_dashboard() is True
    assert page.load_state == page.STATE_SUCCESS
    assert page.last_error_message is None
    assert page.kpi_cards["total_students"].value == 995
