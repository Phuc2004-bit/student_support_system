from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from exceptions import AppError
from models.dto import UserListItem, UserSession
from models.enums import UserRole
from services.user_management_contract import UserManagementContract
from services.permission_service import PermissionService
from ui.dialogs.change_password_dialog import ChangePasswordDialog
from ui.dialogs.profile_dialog import ProfileDialog
from ui.dialogs.user_dialog import UserDialog


class SystemPage(QWidget):
    def __init__(
        self,
        user_service: UserManagementContract | None = None,
        session: UserSession | None = None,
        user_dialog_factory=UserDialog,
        profile_dialog_factory=ProfileDialog,
        change_password_dialog_factory=ChangePasswordDialog,
        permission_service: PermissionService | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.user_service = user_service
        self.session = session
        self.user_dialog_factory = user_dialog_factory
        self.profile_dialog_factory = profile_dialog_factory
        self.change_password_dialog_factory = change_password_dialog_factory
        self.permission_service = permission_service
        self.users: tuple[UserListItem, ...] = ()
        self.own_profile: UserListItem | None = None
        self.setObjectName("systemPage")
        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 24)
        root.setSpacing(16)
        self.title_label = QLabel("Hệ thống", self)
        self.subtitle_label = QLabel("Quản lý tài khoản người dùng.", self)
        self.state_label = QLabel(self)
        self.state_label.setWordWrap(True)
        root.addWidget(self.title_label)
        root.addWidget(self.subtitle_label)
        root.addWidget(self.state_label)
        self.tabs = QTabWidget(self)
        self.profile_tab = QWidget(self.tabs)
        self.users_tab = QWidget(self.tabs)
        self._build_profile_tab()
        self._build_users_tab()
        if self.session is not None:
            self.tabs.addTab(self.profile_tab, "Tài khoản của tôi")
        if self.session is None or self._can_manage_users():
            self.tabs.addTab(self.users_tab, "Người dùng")
        root.addWidget(self.tabs, 1)

    def _build_profile_tab(self) -> None:
        layout = QVBoxLayout(self.profile_tab)
        form = QFormLayout()
        self.profile_username_value = QLineEdit(self.profile_tab)
        self.profile_username_value.setReadOnly(True)
        self.profile_full_name_value = QLineEdit(self.profile_tab)
        self.profile_full_name_value.setReadOnly(True)
        self.profile_role_value = QLineEdit(self.profile_tab)
        self.profile_role_value.setReadOnly(True)
        self.profile_email_value = QLineEdit(self.profile_tab)
        self.profile_email_value.setReadOnly(True)
        self.profile_phone_value = QLineEdit(self.profile_tab)
        self.profile_phone_value.setReadOnly(True)
        self.profile_active_value = QLineEdit(self.profile_tab)
        self.profile_active_value.setReadOnly(True)
        form.addRow("Tên đăng nhập", self.profile_username_value)
        form.addRow("Họ tên", self.profile_full_name_value)
        form.addRow("Vai trò", self.profile_role_value)
        form.addRow("Email", self.profile_email_value)
        form.addRow("Điện thoại", self.profile_phone_value)
        form.addRow("Trạng thái", self.profile_active_value)
        layout.addLayout(form)
        actions = QHBoxLayout()
        self.edit_profile_button = QPushButton("Cập nhật hồ sơ", self.profile_tab)
        self.change_password_button = QPushButton("Đổi mật khẩu", self.profile_tab)
        self.refresh_profile_button = QPushButton("Làm mới", self.profile_tab)
        actions.addWidget(self.edit_profile_button)
        actions.addWidget(self.change_password_button)
        actions.addWidget(self.refresh_profile_button)
        actions.addStretch(1)
        layout.addLayout(actions)
        layout.addStretch(1)

    def _build_users_tab(self) -> None:
        layout = QVBoxLayout(self.users_tab)
        toolbar = QHBoxLayout()
        self.search_input = QLineEdit(self.users_tab)
        self.search_input.setPlaceholderText("Tìm theo tên đăng nhập hoặc họ tên")
        self.search_button = QPushButton("Tìm", self.users_tab)
        self.add_button = QPushButton("Thêm người dùng", self.users_tab)
        self.edit_button = QPushButton("Sửa", self.users_tab)
        self.toggle_button = QPushButton("Vô hiệu/Kích hoạt", self.users_tab)
        self.refresh_button = QPushButton("Làm mới", self.users_tab)
        toolbar.addWidget(self.search_input, 1)
        toolbar.addWidget(self.search_button)
        toolbar.addWidget(self.add_button)
        toolbar.addWidget(self.edit_button)
        toolbar.addWidget(self.toggle_button)
        toolbar.addWidget(self.refresh_button)
        layout.addLayout(toolbar)
        self.user_table = QTableWidget(self.users_tab)
        headers = (
            "Tên đăng nhập",
            "Họ tên",
            "Vai trò",
            "Email",
            "Điện thoại",
            "Trạng thái",
            "Ngày tạo",
            "Cập nhật",
        )
        self.user_table.setColumnCount(len(headers))
        self.user_table.setHorizontalHeaderLabels(headers)
        self.user_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.user_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.user_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.user_table.setAlternatingRowColors(True)
        self.user_table.verticalHeader().setVisible(False)
        self.user_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.user_table.horizontalHeader().setSectionResizeMode(
            1,
            QHeaderView.ResizeMode.Stretch,
        )
        layout.addWidget(self.user_table, 1)

    def _connect_signals(self) -> None:
        self.search_button.clicked.connect(self.refresh_users)
        self.search_input.returnPressed.connect(self.refresh_users)
        self.refresh_button.clicked.connect(self.refresh_users)
        self.add_button.clicked.connect(self.create_user)
        self.edit_button.clicked.connect(self.edit_user)
        self.toggle_button.clicked.connect(self.toggle_user_active)
        self.edit_profile_button.clicked.connect(self.edit_own_profile)
        self.change_password_button.clicked.connect(self.change_own_password)
        self.refresh_profile_button.clicked.connect(self.refresh_own_profile)

    def initialize_system(self) -> bool:
        profile_loaded = self.refresh_own_profile()
        if not self._can_manage_users():
            return profile_loaded
        return self.refresh_users() and profile_loaded

    def initialize_users(self) -> bool:
        return self.refresh_users()

    def refresh_own_profile(self, *_args) -> bool:
        if self.user_service is None or self.session is None:
            self.own_profile = None
            self._render_own_profile()
            self._show_error("Chưa có phiên đăng nhập hợp lệ.")
            return False
        try:
            self.own_profile = self.user_service.get_own_profile(self.session)
        except AppError as exc:
            self.own_profile = None
            self._render_own_profile()
            self._show_error(str(exc))
            return False
        except Exception:
            self.own_profile = None
            self._render_own_profile()
            self._show_error("Không thể tải hồ sơ tài khoản.")
            return False
        self._render_own_profile()
        self.state_label.setText("Đã tải hồ sơ tài khoản.")
        return True

    def _render_own_profile(self) -> None:
        profile = self.own_profile
        role_labels = {
            UserRole.ADMIN: "Quản trị viên",
            UserRole.TEACHER: "Giáo viên",
        }
        self.profile_username_value.setText(profile.username if profile else "")
        self.profile_full_name_value.setText(profile.full_name if profile else "")
        self.profile_role_value.setText(role_labels[profile.role] if profile else "")
        self.profile_email_value.setText(profile.email or "-" if profile else "")
        self.profile_phone_value.setText(profile.phone or "-" if profile else "")
        self.profile_active_value.setText(
            "Đang hoạt động" if profile and profile.is_active else (
                "Ngừng hoạt động" if profile else ""
            )
        )
        self.edit_profile_button.setEnabled(profile is not None)
        self.change_password_button.setEnabled(profile is not None)

    def edit_own_profile(self, *_args) -> bool:
        if self.own_profile is None:
            return False
        dialog = self.profile_dialog_factory(self.own_profile, self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return False
        return self._write_profile(
            lambda: self.user_service.update_own_profile(
                self.session,
                *dialog.values(),
            )
        )

    def change_own_password(self, *_args) -> bool:
        if self.own_profile is None:
            return False
        dialog = self.change_password_dialog_factory(self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return False
        try:
            values = dialog.values()
            return self._write_profile(
                lambda: self.user_service.change_own_password(
                    self.session,
                    *values,
                )
            )
        except AppError as exc:
            self._show_error(str(exc))
            return False
        finally:
            clear = getattr(dialog, "clear_passwords", None)
            if clear is not None:
                clear()

    def _write_profile(self, operation) -> bool:
        if self.user_service is None or self.session is None:
            return False
        try:
            operation()
        except AppError as exc:
            self._show_error(str(exc))
            return False
        except Exception:
            self._show_error("Không thể cập nhật hồ sơ tài khoản.")
            return False
        return self.refresh_own_profile()

    def refresh_users(self, *_args) -> bool:
        if self.user_service is None or self.session is None:
            self.users = ()
            self._render_users()
            self._show_error("Chưa có phiên quản trị hợp lệ.")
            return False
        try:
            self.users = tuple(
                self.user_service.admin_list_users(
                    self.session,
                    self.search_input.text(),
                )
            )
        except AppError as exc:
            self.users = ()
            self._render_users()
            self._show_error(str(exc))
            return False
        except Exception:
            self.users = ()
            self._render_users()
            self._show_error()
            return False
        self._render_users()
        self.state_label.setText(f"Đã tải {len(self.users)} người dùng.")
        return True

    def _render_users(self) -> None:
        role_labels = {
            UserRole.ADMIN: "Quản trị viên",
            UserRole.TEACHER: "Giáo viên",
        }
        self.user_table.setRowCount(len(self.users))
        for row, user in enumerate(self.users):
            values = (
                user.username,
                user.full_name,
                role_labels[user.role],
                user.email or "-",
                user.phone or "-",
                "Đang hoạt động" if user.is_active else "Ngừng hoạt động",
                user.created_at.strftime("%d/%m/%Y %H:%M"),
                user.updated_at.strftime("%d/%m/%Y %H:%M"),
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setData(Qt.ItemDataRole.UserRole, user.user_id)
                self.user_table.setItem(row, column, item)

    def create_user(self, *_args) -> bool:
        dialog = self.user_dialog_factory(None, self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return False
        return self._write(
            lambda: self.user_service.admin_create_user(
                self.session,
                *dialog.create_values(),
            )
        )

    def edit_user(self, *_args) -> bool:
        user = self._selected_user()
        if user is None:
            return False
        dialog = self.user_dialog_factory(user, self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return False
        return self._write(
            lambda: self.user_service.admin_update_user(
                self.session,
                user.user_id,
                *dialog.update_values(),
            )
        )

    def toggle_user_active(self, *_args) -> bool:
        user = self._selected_user()
        if user is None:
            return False
        return self._write(
            lambda: self.user_service.admin_set_user_active(
                self.session,
                user.user_id,
                not user.is_active,
            )
        )

    def _write(self, operation) -> bool:
        if self.user_service is None or self.session is None:
            return False
        try:
            operation()
        except AppError as exc:
            self._show_error(str(exc))
            return False
        except Exception:
            self._show_error()
            return False
        return self.refresh_users()

    def _selected_user(self) -> UserListItem | None:
        row = self.user_table.currentRow()
        if row < 0:
            return None
        user_id = self.user_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        return next((item for item in self.users if item.user_id == user_id), None)

    def _show_error(self, message="Không thể tải hoặc cập nhật người dùng.") -> None:
        self.state_label.setText(message)

    def _can_manage_users(self) -> bool:
        if self.session is None:
            return False
        try:
            permission_service = self.permission_service or PermissionService
            return permission_service.can_manage_users(self.session)
        except AppError:
            return False
