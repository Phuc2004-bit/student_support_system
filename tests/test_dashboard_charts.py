import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from models.dto.dashboard_dto import DashboardStatusItem
from ui.widgets.dashboard_charts import (
    DashboardBarChart,
    DashboardDonutChart,
    status_label,
)


def get_app():
    app = QApplication.instance()
    return app or QApplication([])


def sample_items():
    return (
        DashboardStatusItem(status="DETECTED", count=5),
        DashboardStatusItem(status="IN_PROGRESS", count=8),
        DashboardStatusItem(status="WAITING_REVIEW", count=3),
        DashboardStatusItem(status="COMPLETED", count=10),
    )


def test_status_label_maps_known_statuses():
    assert status_label("DETECTED") == "Mới phát hiện"
    assert status_label("COMPLETED") == "Đã đạt ngưỡng"


def test_status_label_keeps_unknown_status():
    assert status_label("OTHER") == "OTHER"


def test_bar_chart_renders_one_bar_per_status():
    get_app()
    chart = DashboardBarChart()
    chart.set_data(sample_items())

    assert len(chart.axes.patches) == 4
    assert chart.axes.get_ylabel() == "Số hồ sơ"


def test_bar_chart_handles_empty_data():
    get_app()
    chart = DashboardBarChart()
    chart.set_data(())

    assert len(chart.axes.patches) == 0
    assert chart.axes.axison is False


def test_donut_chart_renders_positive_statuses():
    get_app()
    chart = DashboardDonutChart()
    chart.set_data(sample_items())

    assert len(chart.axes.patches) == 4


def test_donut_chart_ignores_zero_values():
    get_app()
    chart = DashboardDonutChart()
    chart.set_data(
        (
            DashboardStatusItem(status="DETECTED", count=0),
            DashboardStatusItem(status="COMPLETED", count=4),
        )
    )

    assert len(chart.axes.patches) == 1


def test_donut_chart_handles_empty_data():
    get_app()
    chart = DashboardDonutChart()
    chart.set_data(())

    assert len(chart.axes.patches) == 0
    assert chart.axes.axison is False
