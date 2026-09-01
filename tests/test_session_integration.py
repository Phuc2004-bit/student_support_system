import os
from contextlib import contextmanager

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PySide6.QtWidgets import QApplication, QDialog

from app_context import AppContext
from main import run_login
from models.dto import UserSession
from models.enums import UserRole


def get_app() -> QApplication:
    app = QApplication.instance()

    if app is None:
        app = QApplication([])

    return app


class FakeDatabase:
    @contextmanager
    def transaction(self):
        yield object()


class FakeAuthService:
    pass


class FakePermissionService:
    pass


def make_session() -> UserSession:
    return UserSession(
        user_id=1,
        username="admin",
        full_name="Quản trị viên",
        role=UserRole.ADMIN,
    )


def make_context() -> AppContext:
    return AppContext(
        db=FakeDatabase(),
        auth_service=FakeAuthService(),
        permission_service=FakePermissionService(),
    )


def test_app_context_starts_without_session():
    context = make_context()

    assert context.session is None
    assert context.is_authenticated is False


def test_app_context_set_and_clear_session():
    context = make_context()
    session = make_session()

    context.set_session(session)

    assert context.session == session
    assert context.is_authenticated is True

    context.clear_session()

    assert context.session is None
    assert context.is_authenticated is False


def test_run_login_success_stores_session():
    get_app()

    context = make_context()
    session = make_session()

    class AcceptedDialog:
        def __init__(self, auth_service):
            assert auth_service is context.auth_service
            self.user_session = session

        def exec(self):
            return QDialog.DialogCode.Accepted

    result = run_login(
        context,
        dialog_factory=AcceptedDialog,
    )

    assert result is True
    assert context.session == session
    assert context.is_authenticated is True


def test_run_login_rejected_clears_existing_session():
    get_app()

    context = make_context()
    context.set_session(make_session())

    class RejectedDialog:
        def __init__(self, auth_service):
            self.user_session = None

        def exec(self):
            return QDialog.DialogCode.Rejected

    result = run_login(
        context,
        dialog_factory=RejectedDialog,
    )

    assert result is False
    assert context.session is None
    assert context.is_authenticated is False


def test_accepted_dialog_without_session_is_rejected_safely():
    get_app()

    context = make_context()

    class BrokenAcceptedDialog:
        def __init__(self, auth_service):
            self.user_session = None

        def exec(self):
            return QDialog.DialogCode.Accepted

    result = run_login(
        context,
        dialog_factory=BrokenAcceptedDialog,
    )

    assert result is False
    assert context.session is None
    assert context.is_authenticated is False
