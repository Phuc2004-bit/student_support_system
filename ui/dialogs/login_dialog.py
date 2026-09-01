from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from models.dto import UserSession


class LoginDialog(QDialog):
    """
    Hộp thoại đăng nhập.

    UI chỉ thu thập dữ liệu và gọi AuthService.
    Không chứa SQL, không hash mật khẩu và không tự xử lý nghiệp vụ xác thực.
    """

    def __init__(
        self,
        auth_service: Any,
        parent=None,
    ):
        super().__init__(parent)

        self.auth_service = auth_service
        self.user_session: UserSession | None = None

        self.setWindowTitle("Đăng nhập")
        self.setModal(True)
        self.setMinimumWidth(420)

        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(28, 24, 28, 24)
        root_layout.setSpacing(16)

        title_label = QLabel("HỆ THỐNG HỖ TRỢ HỌC TẬP")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle_label = QLabel("Đăng nhập để tiếp tục")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        form_layout = QFormLayout()
        form_layout.setHorizontalSpacing(14)
        form_layout.setVerticalSpacing(12)

        self.username_input = QLineEdit()
        self.username_input.setObjectName("username_input")
        self.username_input.setPlaceholderText("Tên đăng nhập")
        self.username_input.setClearButtonEnabled(True)

        self.password_input = QLineEdit()
        self.password_input.setObjectName("password_input")
        self.password_input.setPlaceholderText("Mật khẩu")
        self.password_input.setEchoMode(
            QLineEdit.EchoMode.Password
        )

        form_layout.addRow("Tên đăng nhập:", self.username_input)
        form_layout.addRow("Mật khẩu:", self.password_input)

        self.error_label = QLabel("")
        self.error_label.setObjectName("error_label")
        self.error_label.setWordWrap(True)
        self.error_label.setVisible(False)

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.login_button = QPushButton("Đăng nhập")
        self.login_button.setObjectName("login_button")
        self.login_button.setDefault(True)
        self.login_button.setAutoDefault(True)

        button_layout.addWidget(self.login_button)

        root_layout.addWidget(title_label)
        root_layout.addWidget(subtitle_label)
        root_layout.addLayout(form_layout)
        root_layout.addWidget(self.error_label)
        root_layout.addLayout(button_layout)

        self.username_input.setFocus()

    def _connect_signals(self) -> None:
        self.login_button.clicked.connect(
            self._attempt_login
        )

        self.username_input.returnPressed.connect(
            self._focus_password
        )

        self.password_input.returnPressed.connect(
            self._attempt_login
        )

        self.username_input.textChanged.connect(
            self._clear_error
        )
        self.password_input.textChanged.connect(
            self._clear_error
        )

    def _focus_password(self) -> None:
        if self.password_input.text():
            self._attempt_login()
            return

        self.password_input.setFocus()

    def _attempt_login(self) -> None:
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if not username:
            self._show_error(
                "Vui lòng nhập tên đăng nhập."
            )
            self.username_input.setFocus()
            return

        if not password:
            self._show_error(
                "Vui lòng nhập mật khẩu."
            )
            self.password_input.setFocus()
            return

        self.login_button.setEnabled(False)
        self._clear_error()

        try:
            session = self.auth_service.login(
                username,
                password,
            )
        except Exception as exc:
            self.user_session = None

            # Xóa mật khẩu trước. Việc clear() phát textChanged và
            # _clear_error(), nên phải hiển thị thông báo SAU đó.
            self.password_input.clear()

            self._show_error(
                str(exc) or "Đăng nhập thất bại."
            )
            self.password_input.setFocus()
            return
        finally:
            self.login_button.setEnabled(True)

        self.user_session = session
        self.accept()

    def _show_error(self, message: str) -> None:
        self.error_label.setText(message)
        self.error_label.setVisible(True)

    def _clear_error(self) -> None:
        self.error_label.clear()
        self.error_label.setVisible(False)
