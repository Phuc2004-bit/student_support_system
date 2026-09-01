import os

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PySide6.QtWidgets import QApplication

from ui.pages.dashboard_page import DashboardPage


def get_app() -> QApplication:
    app = QApplication.instance()

    if app is None:
        app = QApplication([])

    return app


def test_dashboard_page_builds_shell_sections():
    get_app()

    page = DashboardPage()

    assert page.title_label.text() == "Tổng quan"
    assert (
        page.subtitle_label.text()
        == "Theo dõi tình hình học sinh cần bổ trợ học tập"
    )

    assert page.filter_frame is not None
    assert page.kpi_frame is not None
    assert page.chart_frame is not None
    assert page.attention_frame is not None


def test_dashboard_page_has_refresh_button():
    get_app()

    page = DashboardPage()

    assert page.refresh_button.text() == "Làm mới"
    assert (
        page.refresh_button.objectName()
        == "dashboardRefreshButton"
    )


def test_dashboard_page_has_stable_object_names_for_future_steps():
    get_app()

    page = DashboardPage()

    assert (
        page.objectName()
        == "dashboardPage"
    )
    assert (
        page.filter_frame.objectName()
        == "dashboardFilterFrame"
    )
    assert (
        page.kpi_frame.objectName()
        == "dashboardKpiFrame"
    )
    assert (
        page.chart_frame.objectName()
        == "dashboardChartFrame"
    )
    assert (
        page.attention_frame.objectName()
        == "dashboardAttentionFrame"
    )
