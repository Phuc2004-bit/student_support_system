import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from models.dto.dashboard_dto import (
    DashboardData,
    DashboardStatusItem,
    DashboardSummary,
)
from ui.pages.dashboard_page import DashboardPage
from ui.widgets.dashboard_charts import (
    DashboardBarChart,
    DashboardDonutChart,
)


def get_app():
    app = QApplication.instance()
    return app or QApplication([])


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
            DashboardStatusItem(status="DETECTED", count=30),
            DashboardStatusItem(status="IN_PROGRESS", count=50),
            DashboardStatusItem(status="COMPLETED", count=40),
        ),
        attention_items=(),
    )


def test_dashboard_page_contains_two_real_charts():
    get_app()
    page = DashboardPage()

    assert isinstance(page.bar_chart, DashboardBarChart)
    assert isinstance(page.donut_chart, DashboardDonutChart)


def test_set_status_breakdown_updates_both_charts():
    get_app()
    page = DashboardPage()

    items = (
        DashboardStatusItem(status="DETECTED", count=2),
        DashboardStatusItem(status="COMPLETED", count=3),
    )
    page.set_status_breakdown(items)

    assert len(page.bar_chart.axes.patches) == 2
    assert len(page.donut_chart.axes.patches) == 2


def test_set_dashboard_data_updates_kpis_and_charts():
    get_app()
    page = DashboardPage()

    page.set_dashboard_data(make_data())

    assert page.kpi_cards["total_students"].value == 1000
    assert page.kpi_cards["needs_support_count"].value == 120
    assert len(page.bar_chart.axes.patches) == 3
    assert len(page.donut_chart.axes.patches) == 3
