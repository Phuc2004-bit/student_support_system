import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from ui.pages.dashboard_page import DashboardPage


def get_app():
    app = QApplication.instance()
    return app or QApplication([])


def test_loading_state_disables_refresh_button():
    get_app()
    page = DashboardPage()

    page._set_loading_state()

    assert page.load_state == page.STATE_LOADING
    assert page.refresh_button.isEnabled() is False
    assert page.state_label.text() == "Đang tải dữ liệu..."


def test_error_state_normalizes_empty_error_message():
    get_app()
    page = DashboardPage()

    page._set_error_state("")

    assert page.load_state == page.STATE_ERROR
    assert page.last_error_message == "Không thể tải dữ liệu Dashboard."
    assert page.refresh_button.isEnabled() is True
