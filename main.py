from __future__ import annotations

import sys
from typing import Callable

from PySide6.QtCore import QEventLoop
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
)

from app_context import AppContext
from bootstrap import build_app_context
from ui.dialogs.login_dialog import LoginDialog
from ui.main_window import MainWindow


def run_login(
    context: AppContext,
    dialog_factory: Callable[..., QDialog] = LoginDialog,
) -> bool:
    dialog = dialog_factory(
        auth_service=context.auth_service
    )
    result = dialog.exec()

    if result != QDialog.DialogCode.Accepted:
        context.clear_session()
        return False

    session = getattr(
        dialog,
        "user_session",
        None,
    )

    if session is None:
        context.clear_session()
        return False

    context.set_session(session)
    return True


def run_main_window(
    context: AppContext,
    window_factory: Callable[..., MainWindow] = MainWindow,
) -> bool:
    """
    Hiển thị MainWindow và chờ đến khi:
    - người dùng logout -> trả về True;
    - người dùng chỉ đóng cửa sổ -> trả về False.
    """

    window = window_factory(
        app_context=context
    )
    event_loop = QEventLoop()

    logged_out = False

    def on_logout() -> None:
        nonlocal logged_out
        logged_out = True
        event_loop.quit()

    def on_window_closed() -> None:
        event_loop.quit()

    window.logout_requested.connect(
        on_logout
    )
    window.window_closed.connect(
        on_window_closed
    )

    window.show()
    event_loop.exec()

    return logged_out


def run_application_flow(
    context: AppContext,
    login_runner: Callable[[AppContext], bool] = run_login,
    window_runner: Callable[[AppContext], bool] = run_main_window,
) -> int:
    """
    Application flow:
    Login -> MainWindow -> Logout -> Login lại.

    Nếu người dùng hủy Login hoặc đóng MainWindow bình thường,
    ứng dụng kết thúc.
    """

    while login_runner(context):
        logged_out = window_runner(context)

        if not logged_out:
            break

    return 0


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    context = build_app_context()
    app.setProperty(
        "app_context",
        context,
    )

    return run_application_flow(
        context
    )


if __name__ == "__main__":
    raise SystemExit(main())
