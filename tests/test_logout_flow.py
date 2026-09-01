import os

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PySide6.QtWidgets import QApplication

from app_context import AppContext
from main import run_application_flow
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


def make_session(
    role: UserRole = UserRole.ADMIN,
) -> UserSession:
    return UserSession(
        user_id=1,
        username="user",
        full_name="Người dùng thử",
        role=role,
    )


def make_context(
    role: UserRole = UserRole.ADMIN,
) -> AppContext:
    return AppContext(
        db=FakeDatabase(),
        auth_service=FakeAuthService(),
        permission_service=PermissionService(),
        session=make_session(role),
    )


def test_topbar_logout_clears_session_and_emits_signal():
    get_app()

    context = make_context()
    window = MainWindow(context)

    received = []
    window.logout_requested.connect(
        lambda: received.append(True)
    )

    window.topbar.logout_button.click()

    assert context.session is None
    assert context.is_authenticated is False
    assert received == [True]


def test_logout_request_is_idempotent():
    get_app()

    context = make_context()
    window = MainWindow(context)

    received = []
    window.logout_requested.connect(
        lambda: received.append(True)
    )

    window.request_logout()
    window.request_logout()

    assert received == [True]
    assert context.session is None


def test_normal_window_close_does_not_clear_session():
    get_app()

    context = make_context()
    window = MainWindow(context)

    window.close()

    assert context.is_authenticated is True
    assert context.session is not None


def test_application_flow_returns_to_login_after_logout():
    context = AppContext(
        db=FakeDatabase(),
        auth_service=FakeAuthService(),
        permission_service=PermissionService(),
    )

    calls = []

    sessions = [
        make_session(UserRole.ADMIN),
        make_session(UserRole.TEACHER),
    ]

    def fake_login(ctx):
        calls.append("login")

        if not sessions:
            ctx.clear_session()
            return False

        ctx.set_session(
            sessions.pop(0)
        )
        return True

    def fake_window(ctx):
        calls.append(
            f"window:{ctx.session.role.value}"
        )
        ctx.clear_session()
        return True

    result = run_application_flow(
        context,
        login_runner=fake_login,
        window_runner=fake_window,
    )

    assert result == 0
    assert calls == [
        "login",
        f"window:{UserRole.ADMIN.value}",
        "login",
        f"window:{UserRole.TEACHER.value}",
        "login",
    ]
    assert context.session is None


def test_application_flow_stops_when_main_window_closed_without_logout():
    context = AppContext(
        db=FakeDatabase(),
        auth_service=FakeAuthService(),
        permission_service=PermissionService(),
    )

    calls = []

    def fake_login(ctx):
        calls.append("login")
        ctx.set_session(
            make_session()
        )
        return True

    def fake_window(ctx):
        calls.append("window")
        return False

    result = run_application_flow(
        context,
        login_runner=fake_login,
        window_runner=fake_window,
    )

    assert result == 0
    assert calls == [
        "login",
        "window",
    ]


def test_application_flow_stops_when_login_is_cancelled():
    context = AppContext(
        db=FakeDatabase(),
        auth_service=FakeAuthService(),
        permission_service=PermissionService(),
    )

    calls = []

    def fake_login(ctx):
        calls.append("login")
        ctx.clear_session()
        return False

    def fake_window(ctx):
        calls.append("window")
        return False

    result = run_application_flow(
        context,
        login_runner=fake_login,
        window_runner=fake_window,
    )

    assert result == 0
    assert calls == ["login"]
    assert context.session is None
