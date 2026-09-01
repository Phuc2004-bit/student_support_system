import os

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PySide6.QtWidgets import QApplication, QDialog

from app_context import AppContext
from main import run_login
from models.dto import UserSession
from models.enums import UserRole
from services.permission_service import PermissionService


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
) -> UserSession:
    if role == UserRole.ADMIN:
        return UserSession(
            user_id=1,
            username="admin",
            full_name="Quản trị viên",
            role=UserRole.ADMIN,
        )

    return UserSession(
        user_id=2,
        username="teacher",
        full_name="Giáo viên",
        role=UserRole.TEACHER,
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


def test_admin_startup_flow_login_session_and_permissions():
    get_app()

    context = make_context()
    admin_session = make_session(UserRole.ADMIN)

    assert context.is_authenticated is False

    logged_in = run_login(
        context,
        dialog_factory=accepted_dialog_factory(
            admin_session
        ),
    )

    assert logged_in is True
    assert context.is_authenticated is True
    assert context.session == admin_session
    assert context.session.role == UserRole.ADMIN

    assert context.can_manage_users() is True
    assert context.can_manage_catalogs() is True
    assert context.can_manage_students() is True
    assert context.can_manage_scores() is True
    assert context.can_manage_support() is True
    assert context.can_view_reports() is True


def test_teacher_startup_flow_login_session_and_permissions():
    get_app()

    context = make_context()
    teacher_session = make_session(
        UserRole.TEACHER
    )

    logged_in = run_login(
        context,
        dialog_factory=accepted_dialog_factory(
            teacher_session
        ),
    )

    assert logged_in is True
    assert context.is_authenticated is True
    assert context.session == teacher_session
    assert context.session.role == UserRole.TEACHER

    assert context.can_manage_users() is False
    assert context.can_manage_catalogs() is False

    assert context.can_manage_students() is True
    assert context.can_manage_scores() is True
    assert context.can_manage_support() is True
    assert context.can_view_reports() is True


def test_cancel_startup_flow_has_no_session_and_no_permissions():
    get_app()

    context = make_context()

    logged_in = run_login(
        context,
        dialog_factory=rejected_dialog_factory(),
    )

    assert logged_in is False
    assert context.is_authenticated is False
    assert context.session is None

    assert context.can_manage_users() is False
    assert context.can_manage_catalogs() is False
    assert context.can_manage_students() is False
    assert context.can_manage_scores() is False
    assert context.can_manage_support() is False
    assert context.can_view_reports() is False
