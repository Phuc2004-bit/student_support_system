import os

import pytest

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PySide6.QtWidgets import QApplication

from models.dto import UserSession
from models.enums import UserRole
from ui.widgets.topbar import Topbar


def get_app() -> QApplication:
    app = QApplication.instance()

    if app is None:
        app = QApplication([])

    return app


def make_session(
    role: UserRole = UserRole.ADMIN,
) -> UserSession:
    return UserSession(
        user_id=1,
        username="user",
        full_name="Người dùng thử",
        role=role,
    )


def test_topbar_requires_session():
    get_app()

    with pytest.raises(ValueError):
        Topbar(None)


def test_topbar_displays_application_title():
    get_app()

    topbar = Topbar(
        make_session()
    )

    assert (
        topbar.app_title_label.text()
        == "Quản lý học sinh cần bổ trợ"
    )


def test_topbar_displays_current_user_name():
    get_app()

    session = make_session()
    topbar = Topbar(session)

    assert (
        topbar.user_label.text()
        == session.full_name
    )


def test_topbar_displays_admin_role_text():
    get_app()

    topbar = Topbar(
        make_session(UserRole.ADMIN)
    )

    assert (
        topbar.role_label.text()
        == "Quản trị viên"
    )


def test_topbar_displays_teacher_role_text():
    get_app()

    topbar = Topbar(
        make_session(UserRole.TEACHER)
    )

    assert (
        topbar.role_label.text()
        == "Giáo viên"
    )


def test_topbar_has_expected_height():
    get_app()

    topbar = Topbar(
        make_session()
    )

    assert (
        topbar.height()
        == Topbar.HEIGHT
    )


def test_topbar_emits_logout_requested():
    get_app()

    topbar = Topbar(
        make_session()
    )

    received = []

    topbar.logout_requested.connect(
        lambda: received.append(True)
    )

    topbar.logout_button.click()

    assert received == [True]
