import os

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PySide6.QtWidgets import QApplication, QDialog

from models.dto import UserSession
from models.enums import UserRole
from ui.dialogs.login_dialog import LoginDialog


def get_app() -> QApplication:
    app = QApplication.instance()

    if app is None:
        app = QApplication([])

    return app


class FakeAuthService:
    def __init__(
        self,
        session=None,
        error: Exception | None = None,
    ):
        self.session = session
        self.error = error
        self.calls = []

    def login(
        self,
        username: str,
        password: str,
    ):
        self.calls.append((username, password))

        if self.error is not None:
            raise self.error

        return self.session


def make_session() -> UserSession:
    return UserSession(
        user_id=1,
        username="admin",
        full_name="Quản trị viên",
        role=UserRole.ADMIN,
    )


def test_login_success_accepts_dialog_and_stores_session():
    get_app()

    session = make_session()
    auth = FakeAuthService(session=session)
    dialog = LoginDialog(auth_service=auth)

    dialog.username_input.setText(" admin ")
    dialog.password_input.setText("secret123")

    dialog._attempt_login()

    assert auth.calls == [
        ("admin", "secret123")
    ]
    assert dialog.user_session == session
    assert dialog.result() == QDialog.DialogCode.Accepted


def test_missing_username_is_blocked_before_auth_service():
    get_app()

    auth = FakeAuthService(session=make_session())
    dialog = LoginDialog(auth_service=auth)

    dialog.password_input.setText("secret123")
    dialog._attempt_login()

    assert auth.calls == []
    assert dialog.user_session is None
    assert dialog.error_label.isHidden() is False
    assert "tên đăng nhập" in dialog.error_label.text().lower()


def test_missing_password_is_blocked_before_auth_service():
    get_app()

    auth = FakeAuthService(session=make_session())
    dialog = LoginDialog(auth_service=auth)

    dialog.username_input.setText("admin")
    dialog._attempt_login()

    assert auth.calls == []
    assert dialog.user_session is None
    assert dialog.error_label.isHidden() is False
    assert "mật khẩu" in dialog.error_label.text().lower()


def test_login_failure_keeps_dialog_open_and_clears_password():
    get_app()

    auth = FakeAuthService(
        error=ValueError(
            "Tên đăng nhập hoặc mật khẩu không đúng."
        )
    )

    dialog = LoginDialog(auth_service=auth)

    dialog.username_input.setText("admin")
    dialog.password_input.setText("wrong")
    dialog._attempt_login()

    assert auth.calls == [
        ("admin", "wrong")
    ]
    assert dialog.user_session is None
    assert (
        dialog.result()
        != QDialog.DialogCode.Accepted
    )
    assert dialog.password_input.text() == ""
    assert dialog.error_label.isHidden() is False
    assert "không đúng" in dialog.error_label.text().lower()


def test_changing_input_clears_previous_error():
    get_app()

    auth = FakeAuthService(session=make_session())
    dialog = LoginDialog(auth_service=auth)

    dialog._show_error("Lỗi thử nghiệm")

    assert dialog.error_label.isHidden() is False

    dialog.username_input.setText("admin")

    assert dialog.error_label.isHidden() is True
    assert dialog.error_label.text() == ""
