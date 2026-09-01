import os

import pytest

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PySide6.QtWidgets import (
    QApplication,
    QDialog,
)

from app_context import AppContext
from main import run_login
from models.dto import UserSession
from models.enums import UserRole
from services.permission_service import PermissionService
from ui.main_window import MainWindow


def get_app() -> QApplication:
    app = QApplication.instance()

    if app is None:
        app = QApplication([])

    return app


class FakeDatabase:
    pass


class FakeAuthService:
    pass


def make_context() -> AppContext:
    return AppContext(
        db=FakeDatabase(),
        auth_service=FakeAuthService(),
        permission_service=PermissionService(),
    )


def make_session(
    role: UserRole,
    *,
    user_id: int,
    username: str,
    full_name: str,
) -> UserSession:
    return UserSession(
        user_id=user_id,
        username=username,
        full_name=full_name,
        role=role,
    )


def accepted_dialog_factory(
    session: UserSession,
):
    class AcceptedDialog:
        def __init__(self, auth_service):
            self.auth_service = auth_service
            self.user_session = session

        def exec(self):
            return QDialog.DialogCode.Accepted

    return AcceptedDialog


def rejected_dialog_factory():
    class RejectedDialog:
        def __init__(self, auth_service):
            self.auth_service = auth_service
            self.user_session = None

        def exec(self):
            return QDialog.DialogCode.Rejected

    return RejectedDialog


def test_admin_login_main_window_navigation_and_logout_integration():
    get_app()

    context = make_context()
    session = make_session(
        UserRole.ADMIN,
        user_id=1,
        username="admin",
        full_name="Quản trị viên A",
    )

    assert run_login(
        context,
        dialog_factory=accepted_dialog_factory(session),
    ) is True

    window = MainWindow(context)

    assert context.is_authenticated is True
    assert window.topbar.user_label.text() == "Quản trị viên A"
    assert window.topbar.role_label.text() == "Quản trị viên"

    for key in (
        "dashboard",
        "students",
        "scores",
        "support",
        "reports",
        "catalogs",
        "system",
    ):
        assert window.can_navigate_to(key) is True
        assert not window.sidebar.button(key).isHidden()

    window.navigate_to("system")

    assert window.page_stack.current_key == "system"
    assert window.sidebar.current_key == "system"

    window.topbar.logout_button.click()

    assert context.is_authenticated is False
    assert context.session is None


def test_teacher_login_permissions_navigation_and_logout_integration():
    get_app()

    context = make_context()
    session = make_session(
        UserRole.TEACHER,
        user_id=2,
        username="teacher",
        full_name="Giáo viên B",
    )

    assert run_login(
        context,
        dialog_factory=accepted_dialog_factory(session),
    ) is True

    window = MainWindow(context)

    assert window.topbar.user_label.text() == "Giáo viên B"
    assert window.topbar.role_label.text() == "Giáo viên"

    for key in (
        "dashboard",
        "students",
        "scores",
        "support",
        "reports",
    ):
        assert window.can_navigate_to(key) is True
        assert not window.sidebar.button(key).isHidden()

    for key in (
        "catalogs",
        "system",
    ):
        assert window.can_navigate_to(key) is False
        assert window.sidebar.button(key).isHidden()

    window.sidebar.button("support").click()

    assert window.page_stack.current_key == "support"

    with pytest.raises(PermissionError):
        window.navigate_to("system")

    assert window.page_stack.current_key == "support"

    window.topbar.logout_button.click()

    assert context.session is None
    assert context.is_authenticated is False


def test_cancelled_login_cannot_open_main_window():
    get_app()

    context = make_context()

    assert run_login(
        context,
        dialog_factory=rejected_dialog_factory(),
    ) is False

    assert context.session is None
    assert context.is_authenticated is False

    with pytest.raises(PermissionError):
        MainWindow(context)


def test_relogin_rebuilds_ui_permissions_from_new_session():
    get_app()

    context = make_context()

    admin_session = make_session(
        UserRole.ADMIN,
        user_id=1,
        username="admin",
        full_name="Admin",
    )

    teacher_session = make_session(
        UserRole.TEACHER,
        user_id=2,
        username="teacher",
        full_name="Teacher",
    )

    assert run_login(
        context,
        dialog_factory=accepted_dialog_factory(admin_session),
    ) is True

    admin_window = MainWindow(context)

    assert admin_window.can_navigate_to("system") is True
    assert not admin_window.sidebar.button("system").isHidden()

    admin_window.request_logout()

    assert context.session is None

    assert run_login(
        context,
        dialog_factory=accepted_dialog_factory(teacher_session),
    ) is True

    teacher_window = MainWindow(context)

    assert teacher_window.topbar.role_label.text() == "Giáo viên"
    assert teacher_window.can_navigate_to("system") is False
    assert teacher_window.sidebar.button("system").isHidden()
    assert teacher_window.can_navigate_to("support") is True

    teacher_window.request_logout()

    assert context.session is None
