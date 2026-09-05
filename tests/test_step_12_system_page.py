from datetime import datetime
import inspect
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialog, QLineEdit, QTabWidget

from exceptions import ValidationError
from models.dto import UserListItem, UserSession
from models.enums import UserRole
from ui.dialogs.user_dialog import UserDialog
from ui.main_window import MainWindow
from ui.pages.system_page import SystemPage


NOW = datetime(2042, 1, 2, 3, 4, 5)


def app():
    return QApplication.instance() or QApplication([])


def session(role=UserRole.ADMIN):
    return UserSession(1 if role == UserRole.ADMIN else 2, "actor", "Actor", role)


def item(user_id=2, role=UserRole.TEACHER, active=True):
    return UserListItem(
        user_id,
        f"user_{user_id}",
        f"User {user_id}",
        role,
        f"u{user_id}@example.com",
        "0901234567",
        active,
        NOW,
        NOW,
    )


class UserServiceStub:
    def __init__(self):
        self.users = [item(1, UserRole.ADMIN), item(2), item(3, active=False)]
        self.calls = []
        self.fail = False

    def admin_list_users(self, actor, search=None):
        self.calls.append(("list", actor, search))
        if self.fail:
            raise RuntimeError("raw pyodbc secret")
        return [
            user
            for user in self.users
            if not search
            or search.strip().lower() in user.username.lower()
            or search.strip().lower() in user.full_name.lower()
        ]

    def admin_create_user(self, actor, *values):
        self.calls.append(("create", actor, *values))

    def admin_update_user(self, actor, *values):
        self.calls.append(("update", actor, *values))

    def admin_set_user_active(self, actor, *values):
        self.calls.append(("active", actor, *values))


class AcceptedDialog:
    DialogCode = QDialog.DialogCode

    def __init__(self, user, _parent):
        self.user = user

    def exec(self):
        return self.DialogCode.Accepted

    def create_values(self):
        return (
            "new_teacher",
            "Password@123",
            "New Teacher",
            UserRole.TEACHER,
            None,
            None,
            True,
        )

    def update_values(self):
        return ("Updated", UserRole.ADMIN, "updated@example.com", None)


def test_system_page_builds_user_tab_without_main_window_integration():
    app()
    page = SystemPage()

    assert page.title_label.text() == "Hệ thống"
    assert isinstance(page.tabs, QTabWidget)
    assert page.tabs.count() == 1
    assert page.tabs.tabText(0) == "Người dùng"
    assert "SystemPage" not in inspect.getsource(MainWindow)


def test_user_list_loads_through_service_and_never_renders_hash():
    app()
    service = UserServiceStub()
    actor = session()
    page = SystemPage(service, actor)

    assert page.initialize_users() is True
    assert service.calls[-1] == ("list", actor, "")
    assert page.user_table.rowCount() == 3
    headers = [
        page.user_table.horizontalHeaderItem(column).text()
        for column in range(page.user_table.columnCount())
    ]
    table_text = " ".join(
        page.user_table.item(row, column).text()
        for row in range(page.user_table.rowCount())
        for column in range(page.user_table.columnCount())
    )
    assert all("password" not in header.lower() for header in headers)
    assert "$2" not in table_text
    assert "hash" not in table_text.lower()


def test_user_rows_preserve_id_and_render_roles_status_and_metadata():
    app()
    page = SystemPage(UserServiceStub(), session())
    page.initialize_users()

    assert page.user_table.item(0, 0).data(Qt.ItemDataRole.UserRole) == 1
    assert page.user_table.item(0, 2).text() == "Quản trị viên"
    assert page.user_table.item(1, 2).text() == "Giáo viên"
    assert page.user_table.item(1, 5).text() == "Đang hoạt động"
    assert page.user_table.item(2, 5).text() == "Ngừng hoạt động"
    assert page.user_table.item(0, 6).text() == "02/01/2042 03:04"


def test_search_is_delegated_to_user_service():
    app()
    service = UserServiceStub()
    page = SystemPage(service, session())
    page.search_input.setText(" user_2 ")

    assert page.refresh_users() is True
    assert service.calls[-1][2] == " user_2 "
    assert page.user_table.rowCount() == 1


def test_create_passes_initial_password_and_enum_to_protected_service_api():
    app()
    service = UserServiceStub()
    actor = session()
    page = SystemPage(service, actor, AcceptedDialog)

    assert page.create_user() is True
    create_call = next(call for call in service.calls if call[0] == "create")
    assert create_call[1] == actor
    assert create_call[2] == "new_teacher"
    assert create_call[5] == UserRole.TEACHER


def test_edit_locks_identity_and_sends_selected_id_with_safe_fields_only():
    app()
    service = UserServiceStub()
    page = SystemPage(service, session(), AcceptedDialog)
    page.initialize_users()
    page.user_table.setCurrentCell(1, 0)

    assert page.edit_user() is True
    update_call = next(call for call in service.calls if call[0] == "update")
    assert update_call[2:] == (
        2,
        "Updated",
        UserRole.ADMIN,
        "updated@example.com",
        None,
    )
    assert "Password@123" not in repr(update_call)


def test_toggle_uses_selected_id_and_inverse_active_state():
    app()
    service = UserServiceStub()
    page = SystemPage(service, session(), AcceptedDialog)
    page.initialize_users()
    page.user_table.setCurrentCell(2, 0)

    assert page.toggle_user_active() is True
    assert next(call for call in service.calls if call[0] == "active")[2:] == (3, True)


def test_user_dialog_uses_role_enum_and_password_is_never_visible_on_edit():
    app()
    create_dialog = UserDialog()
    edit_dialog = UserDialog(item())

    assert create_dialog.role_combo.itemData(0) == UserRole.ADMIN
    assert create_dialog.role_combo.itemData(1) == UserRole.TEACHER
    assert create_dialog.password_input.echoMode() == QLineEdit.EchoMode.Password
    assert not edit_dialog.username_input.isEnabled()
    assert not edit_dialog.password_input.isVisible()
    assert not edit_dialog.active_checkbox.isEnabled()
    assert len(edit_dialog.update_values()) == 4


def test_missing_session_and_service_errors_are_safe_empty_states():
    app()
    assert SystemPage(UserServiceStub(), None).initialize_users() is False

    service = UserServiceStub()
    service.fail = True
    page = SystemPage(service, session())
    assert page.initialize_users() is False
    assert page.user_table.rowCount() == 0
    assert "pyodbc" not in page.state_label.text().lower()
    assert "secret" not in page.state_label.text().lower()


def test_teacher_denial_from_service_is_rendered_without_bypass():
    app()

    class DeniedService(UserServiceStub):
        def admin_list_users(self, actor, search=None):
            raise ValidationError("Bạn không có quyền quản lý tài khoản.")

    page = SystemPage(DeniedService(), session(UserRole.TEACHER))
    assert page.initialize_users() is False
    assert "không có quyền" in page.state_label.text()


def test_ui_has_no_sql_repository_or_password_hash_dependency():
    page_source = inspect.getsource(SystemPage)
    dialog_source = inspect.getsource(UserDialog)
    combined = f"{page_source}\n{dialog_source}".lower()

    assert "select " not in combined
    assert "insert " not in combined
    assert "update dbo" not in combined
    assert "repository" not in combined
    assert "password_hash" not in combined
