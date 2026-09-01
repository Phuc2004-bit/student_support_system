import os

import pytest

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PySide6.QtWidgets import QApplication

from ui.widgets.sidebar import Sidebar


def get_app() -> QApplication:
    app = QApplication.instance()

    if app is None:
        app = QApplication([])

    return app


def test_sidebar_contains_all_v1_items():
    get_app()

    sidebar = Sidebar()

    expected = {
        "dashboard": "Tổng quan",
        "students": "Học sinh",
        "scores": "Điểm & Đánh giá",
        "support": "Bổ trợ học tập",
        "reports": "Báo cáo & Thống kê",
        "catalogs": "Danh mục",
        "system": "Hệ thống",
    }

    assert len(sidebar.ITEMS) == 7

    for key, text in expected.items():
        assert sidebar.button(key).text() == text


def test_dashboard_is_selected_by_default():
    get_app()

    sidebar = Sidebar()

    assert sidebar.current_key == "dashboard"
    assert sidebar.button("dashboard").isChecked()


def test_sidebar_emits_navigation_key_on_click():
    get_app()

    sidebar = Sidebar()
    received = []

    sidebar.navigation_requested.connect(
        received.append
    )

    sidebar.button("students").click()

    assert received == ["students"]
    assert sidebar.current_key == "students"


def test_sidebar_selection_is_exclusive():
    get_app()

    sidebar = Sidebar()

    sidebar.button("scores").click()

    assert sidebar.button("scores").isChecked()
    assert not sidebar.button("dashboard").isChecked()

    sidebar.button("support").click()

    assert sidebar.button("support").isChecked()
    assert not sidebar.button("scores").isChecked()


def test_sidebar_supports_future_permission_visibility():
    get_app()

    sidebar = Sidebar()

    sidebar.set_item_visible(
        "system",
        False,
    )

    assert sidebar.button("system").isHidden()

    sidebar.set_item_visible(
        "system",
        True,
    )

    assert not sidebar.button("system").isHidden()


def test_sidebar_rejects_unknown_key():
    get_app()

    sidebar = Sidebar()

    with pytest.raises(KeyError):
        sidebar.button("not-exist")
