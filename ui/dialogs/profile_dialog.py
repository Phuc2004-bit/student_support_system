from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from models.dto import UserListItem
from models.enums import UserRole


class ProfileDialog(QDialog):
    def __init__(
        self,
        profile: UserListItem,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.profile = profile
        self.setWindowTitle("Cập nhật hồ sơ")

        self.username_input = QLineEdit(profile.username, self)
        self.username_input.setReadOnly(True)
        self.role_input = QLineEdit(self._role_label(profile.role), self)
        self.role_input.setReadOnly(True)
        self.full_name_input = QLineEdit(profile.full_name, self)
        self.full_name_input.setMaxLength(100)
        self.email_input = QLineEdit(profile.email or "", self)
        self.email_input.setMaxLength(100)
        self.phone_input = QLineEdit(profile.phone or "", self)
        self.phone_input.setMaxLength(20)

        form = QFormLayout()
        form.addRow("Tên đăng nhập", self.username_input)
        form.addRow("Vai trò", self.role_input)
        form.addRow("Họ tên *", self.full_name_input)
        form.addRow("Email", self.email_input)
        form.addRow("Điện thoại", self.phone_input)
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel,
            self,
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        root = QVBoxLayout(self)
        root.addLayout(form)
        root.addWidget(self.button_box)

    def values(self) -> tuple[str, str | None, str | None]:
        return (
            self.full_name_input.text(),
            self.email_input.text() or None,
            self.phone_input.text() or None,
        )

    @staticmethod
    def _role_label(role: UserRole) -> str:
        return {
            UserRole.ADMIN: "Quản trị viên",
            UserRole.TEACHER: "Giáo viên",
        }[role]
