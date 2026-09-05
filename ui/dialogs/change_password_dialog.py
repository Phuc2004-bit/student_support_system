from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from exceptions import ValidationError


class ChangePasswordDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Đổi mật khẩu")
        self.current_password_input = self._password_input()
        self.new_password_input = self._password_input()
        self.confirm_password_input = self._password_input()
        self.error_label = QLabel(self)
        self.error_label.setWordWrap(True)

        form = QFormLayout()
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
        root = QVBoxLayout(self)
        root.addLayout(form)
        root.addWidget(self.error_label)
        root.addWidget(self.button_box)

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
