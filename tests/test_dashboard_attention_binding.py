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
from ui.widgets.dashboard_attention import DashboardAttentionTable


def get_app():
    app = QApplication.instance()
    return app or QApplication([])


def make_attention():
    return DashboardAttentionItem(
        intervention_id=15,
        student_code="HS015",
        full_name="Trần Thị B",
        grade_number=7,
        class_name="7A2",
        subject_code="VAN",
        subject_name="Ngữ văn",
        status="CONTINUE",
        detected_date=date(2026, 9, 20),
        trigger_score=Decimal("3.10"),
        latest_review_score=Decimal("3.30"),
    )


def make_data():
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
                status="CONTINUE",
                count=10,
            ),
        ),
        attention_items=(make_attention(),),
    )


def test_dashboard_page_contains_attention_table():
    get_app()
    page = DashboardPage()

    assert isinstance(
        page.attention_table,
        DashboardAttentionTable,
    )


def test_set_attention_items_updates_table():
    get_app()
    page = DashboardPage()

    page.set_attention_items(
        (make_attention(),)
    )

    assert page.attention_table.table.rowCount() == 1
    assert (
        page.attention_table.table.item(0, 4).text()
        == "Cần tiếp tục"
    )


def test_set_dashboard_data_updates_attention_too():
    get_app()
    page = DashboardPage()

    page.set_dashboard_data(make_data())

    assert page.kpi_cards["total_students"].value == 1000
    assert len(page.bar_chart.axes.patches) == 1
    assert page.attention_table.table.rowCount() == 1
    assert page.attention_table.intervention_id_at_row(0) == 15
