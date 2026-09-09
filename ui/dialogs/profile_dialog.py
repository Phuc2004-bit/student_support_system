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

from models.dto import UserListItem
from models.enums import UserRole
from ui.theme import dialog_stylesheet


class ProfileDialog(QDialog):
    def __init__(
        self,
        profile: UserListItem,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.profile = profile
        self.setObjectName("profileDialog")
        self.setWindowTitle("Cập nhật hồ sơ")
        self.resize(520, 480)
        self.title_label = QLabel("Cập nhật hồ sơ", self)
        self.title_label.setProperty("dialogTitle", True)
        self.subtitle_label = QLabel(
            "Tên đăng nhập và vai trò được hệ thống quản lý và không thể chỉnh sửa.", self
        )
        self.subtitle_label.setProperty("dialogSubtitle", True)
        self.subtitle_label.setWordWrap(True)

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

        self.form_card = QFrame(self)
        self.form_card.setProperty("dialogCard", True)
        form = QFormLayout(self.form_card)
        form.setContentsMargins(20, 18, 20, 18)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(12)
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
        self.save_button = self.button_box.button(QDialogButtonBox.StandardButton.Save)
        self.cancel_button = self.button_box.button(QDialogButtonBox.StandardButton.Cancel)
        self.save_button.setText("Lưu")
        self.cancel_button.setText("Hủy")
        self.save_button.setProperty("variant", "primary")
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(14)
        root.addWidget(self.title_label)
        root.addWidget(self.subtitle_label)
        root.addWidget(self.form_card)
        root.addWidget(self.button_box)
        self.setStyleSheet(dialog_stylesheet())

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
