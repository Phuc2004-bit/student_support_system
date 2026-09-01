import os

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PySide6.QtWidgets import QApplication

from app_context import AppContext
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


def make_context(
    role: UserRole,
    full_name: str,
) -> AppContext:
    return AppContext(
        db=FakeDatabase(),
        auth_service=FakeAuthService(),
        permission_service=PermissionService(),
        session=UserSession(
            user_id=1,
            username="user",
            full_name=full_name,
            role=role,
        ),
    )


def test_admin_session_is_reflected_in_topbar():
    get_app()

    context = make_context(
        UserRole.ADMIN,
        "Nguyễn Văn Admin",
    )
    window = MainWindow(context)

    assert (
        window.topbar.user_label.text()
        == "Nguyễn Văn Admin"
    )
    assert (
        window.topbar.role_label.text()
        == "Quản trị viên"
    )


def test_teacher_session_is_reflected_in_topbar():
    get_app()

    context = make_context(
        UserRole.TEACHER,
        "Trần Thị Giáo viên",
    )
    window = MainWindow(context)

    assert (
        window.topbar.user_label.text()
        == "Trần Thị Giáo viên"
    )
    assert (
        window.topbar.role_label.text()
        == "Giáo viên"
    )


def test_topbar_uses_same_session_from_context():
    get_app()

    context = make_context(
        UserRole.TEACHER,
        "Giáo viên A",
    )
    window = MainWindow(context)

    assert (
        window.topbar.session
        is context.session
    )
