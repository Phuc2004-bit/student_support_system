from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from exceptions import ValidationError
from ui.theme import dialog_stylesheet


class ChangePasswordDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("changePasswordDialog")
        self.setWindowTitle("Đổi mật khẩu")
        self.resize(520, 420)
        self.title_label = QLabel("Đổi mật khẩu", self)
        self.title_label.setProperty("dialogTitle", True)
        self.subtitle_label = QLabel(
            "Xác nhận mật khẩu hiện tại trước khi thiết lập mật khẩu mới.", self
        )
        self.subtitle_label.setProperty("dialogSubtitle", True)
        self.current_password_input = self._password_input()
        self.new_password_input = self._password_input()
        self.confirm_password_input = self._password_input()
        self.error_label = QLabel(self)
        self.error_label.setWordWrap(True)

        self.form_card = QFrame(self)
        self.form_card.setProperty("dialogCard", True)
        form = QFormLayout(self.form_card)
        form.setContentsMargins(20, 18, 20, 18)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(12)
        form.addRow("Mật khẩu hiện tại *", self.current_password_input)
        form.addRow("Mật khẩu mới *", self.new_password_input)
        form.addRow("Xác nhận mật khẩu mới *", self.confirm_password_input)
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        self.button_box.accepted.connect(self._accept_if_valid)
        self.button_box.rejected.connect(self._reject_and_clear)
        self.save_button = self.button_box.button(QDialogButtonBox.StandardButton.Save)
        self.cancel_button = self.button_box.button(QDialogButtonBox.StandardButton.Cancel)
        self.save_button.setText("Đổi mật khẩu")
        self.cancel_button.setText("Hủy")
        self.save_button.setProperty("variant", "primary")
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(14)
        root.addWidget(self.title_label)
        root.addWidget(self.subtitle_label)
        root.addWidget(self.form_card)
        root.addWidget(self.error_label)
        root.addWidget(self.button_box)
        self.setStyleSheet(dialog_stylesheet())

    def values(self) -> tuple[str, str]:
        current_password = self.current_password_input.text()
        new_password = self.new_password_input.text()
        confirm_password = self.confirm_password_input.text()
        if not current_password or not new_password or not confirm_password:
            raise ValidationError("Vui lòng nhập đầy đủ thông tin mật khẩu.")
        if new_password != confirm_password:
            raise ValidationError("Xác nhận mật khẩu mới không khớp.")
        return current_password, new_password

    def clear_passwords(self) -> None:
        self.current_password_input.clear()
        self.new_password_input.clear()
        self.confirm_password_input.clear()

    def _accept_if_valid(self) -> None:
        try:
            self.values()
        except ValidationError as exc:
            self.error_label.setText(str(exc))
            return
        self.error_label.clear()
        self.accept()

    def _reject_and_clear(self) -> None:
        self.clear_passwords()
        self.reject()

    def _password_input(self) -> QLineEdit:
        field = QLineEdit(self)
        field.setEchoMode(QLineEdit.EchoMode.Password)
        field.setMaxLength(72)
        return field
