from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
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


class UserDialog(QDialog):
    def __init__(
        self,
        user: UserListItem | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.user = user
        self.setObjectName("userDialog")
        self.setWindowTitle("Sửa người dùng" if user else "Thêm người dùng")
        self.resize(540, 560)
        self.title_label = QLabel(
            "Cập nhật người dùng" if user else "Thêm người dùng mới", self
        )
        self.title_label.setProperty("dialogTitle", True)
        self.subtitle_label = QLabel(
            "Chỉ quản lý thông tin tài khoản, vai trò và trạng thái được hệ thống cho phép.",
            self,
        )
        self.subtitle_label.setProperty("dialogSubtitle", True)
        self.subtitle_label.setWordWrap(True)
        self.username_input = QLineEdit(self)
        self.username_input.setMaxLength(50)
        self.password_input = QLineEdit(self)
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setMaxLength(72)
        self.full_name_input = QLineEdit(self)
        self.full_name_input.setMaxLength(100)
        self.role_combo = QComboBox(self)
        self.role_combo.addItem("Quản trị viên", UserRole.ADMIN)
        self.role_combo.addItem("Giáo viên", UserRole.TEACHER)
        self.email_input = QLineEdit(self)
        self.email_input.setMaxLength(100)
        self.phone_input = QLineEdit(self)
        self.phone_input.setMaxLength(20)
        self.active_checkbox = QCheckBox("Đang hoạt động", self)
        self.active_checkbox.setChecked(True)

        self.form_card = QFrame(self)
        self.form_card.setProperty("dialogCard", True)
        form = QFormLayout(self.form_card)
        form.setContentsMargins(20, 18, 20, 18)
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(12)
        form.addRow("Tên đăng nhập *", self.username_input)
        form.addRow("Mật khẩu ban đầu *", self.password_input)
        form.addRow("Họ tên *", self.full_name_input)
        form.addRow("Vai trò *", self.role_combo)
        form.addRow("Email", self.email_input)
        form.addRow("Điện thoại", self.phone_input)
        form.addRow("", self.active_checkbox)
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

        if user is not None:
            self.username_input.setText(user.username)
            self.username_input.setEnabled(False)
            self.password_input.clear()
            self.password_input.setEnabled(False)
            self.password_input.setVisible(False)
            form.labelForField(self.password_input).setVisible(False)
            self.full_name_input.setText(user.full_name)
            self.role_combo.setCurrentIndex(self.role_combo.findData(user.role))
            self.email_input.setText(user.email or "")
            self.phone_input.setText(user.phone or "")
            self.active_checkbox.setChecked(user.is_active)
            self.active_checkbox.setEnabled(False)
        self.setStyleSheet(dialog_stylesheet())

    def create_values(self):
        if self.user is not None:
            raise RuntimeError("Dialog đang ở chế độ sửa.")
        return (
            self.username_input.text(),
            self.password_input.text(),
            self.full_name_input.text(),
            self.role_combo.currentData(),
            self.email_input.text() or None,
            self.phone_input.text() or None,
            self.active_checkbox.isChecked(),
        )

    def update_values(self):
        if self.user is None:
            raise RuntimeError("Dialog đang ở chế độ tạo.")
        return (
            self.full_name_input.text(),
            self.role_combo.currentData(),
            self.email_input.text() or None,
            self.phone_input.text() or None,
        )
