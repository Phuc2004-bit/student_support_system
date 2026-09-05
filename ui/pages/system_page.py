from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
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
from ui.dialogs.user_dialog import UserDialog


class SystemPage(QWidget):
    def __init__(
        self,
        user_service: UserManagementContract | None = None,
        session: UserSession | None = None,
        user_dialog_factory=UserDialog,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.user_service = user_service
        self.session = session
        self.user_dialog_factory = user_dialog_factory
        self.users: tuple[UserListItem, ...] = ()
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
        self.users_tab = QWidget(self.tabs)
        self.tabs.addTab(self.users_tab, "Người dùng")
        root.addWidget(self.tabs, 1)

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

    def initialize_users(self) -> bool:
        return self.refresh_users()

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
