from datetime import datetime
import inspect
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QDialog, QLineEdit

from exceptions import ValidationError
from models.dto import UserListItem, UserSession
from models.enums import UserRole
from ui.dialogs.change_password_dialog import ChangePasswordDialog
from ui.dialogs.profile_dialog import ProfileDialog
from ui.main_window import MainWindow
from ui.pages.system_page import SystemPage


NOW = datetime(2042, 2, 3, 4, 5, 6)


def app():
    return QApplication.instance() or QApplication([])


def session(role=UserRole.ADMIN):
    return UserSession(1, "account_user", "Account User", role)


def profile(role=UserRole.ADMIN, active=True):
    return UserListItem(
        1,
        "account_user",
        "Account User",
        role,
        "account@example.com",
        "0901234567",
        active,
        NOW,
        NOW,
    )


class AccountServiceStub:
    def __init__(self, role=UserRole.ADMIN):
        self.profile = profile(role)
        self.calls = []

    def get_own_profile(self, actor):
        self.calls.append(("profile", actor))
        return self.profile

    def update_own_profile(self, actor, full_name, email, phone):
        self.calls.append(("update_profile", actor, full_name, email, phone))
        self.profile = UserListItem(
            self.profile.user_id,
            self.profile.username,
            full_name,
            self.profile.role,
            email,
            phone,
            self.profile.is_active,
            self.profile.created_at,
            NOW,
        )
        return self.profile

    def change_own_password(self, actor, current_password, new_password):
        self.calls.append(("password", actor, current_password, new_password))
        return self.profile

    def admin_list_users(self, actor, search=None):
        self.calls.append(("list", actor, search))
        return [self.profile]


class AcceptedProfileDialog:
    DialogCode = QDialog.DialogCode

    def __init__(self, profile_item, _parent):
        self.profile = profile_item

    def exec(self):
        return self.DialogCode.Accepted

    def values(self):
        return "Updated Name", "updated@example.com", "0912345678"


class AcceptedPasswordDialog:
    DialogCode = QDialog.DialogCode
    instance = None

    def __init__(self, _parent):
        self.cleared = False
        type(self).instance = self

    def exec(self):
        return self.DialogCode.Accepted

    def values(self):
        return "Current@123", "Different@456"

    def clear_passwords(self):
        self.cleared = True


def test_admin_sees_profile_and_user_management_tabs():
    app()
    page = SystemPage(AccountServiceStub(), session())

    assert [page.tabs.tabText(index) for index in range(page.tabs.count())] == [
        "Tài khoản của tôi",
        "Người dùng",
    ]
    assert "SystemPage" not in inspect.getsource(MainWindow)


def test_teacher_sees_only_own_account_tab_and_no_management_call():
    app()
    actor = session(UserRole.TEACHER)
    service = AccountServiceStub(UserRole.TEACHER)
    page = SystemPage(service, actor)

    assert page.tabs.count() == 1
    assert page.tabs.tabText(0) == "Tài khoản của tôi"
    assert page.initialize_system() is True
    assert not any(call[0] == "list" for call in service.calls)


@pytest.mark.parametrize("role", [UserRole.ADMIN, UserRole.TEACHER])
def test_profile_loads_current_admin_or_teacher_without_hash(role):
    app()
    service = AccountServiceStub(role)
    page = SystemPage(service, session(role))

    assert page.refresh_own_profile() is True
    assert page.profile_username_value.text() == "account_user"
    assert page.profile_full_name_value.text() == "Account User"
    assert page.profile_role_value.text() in {"Quản trị viên", "Giáo viên"}
    assert page.profile_active_value.text() == "Đang hoạt động"
    rendered = " ".join(
        field.text()
        for field in (
            page.profile_username_value,
            page.profile_full_name_value,
            page.profile_role_value,
            page.profile_email_value,
            page.profile_phone_value,
            page.profile_active_value,
        )
    )
    assert "hash" not in rendered.lower()
    assert "$2" not in rendered


def test_profile_display_and_dialog_keep_username_and_role_read_only():
    app()
    page = SystemPage(AccountServiceStub(), session())
    dialog = ProfileDialog(profile())

    assert page.profile_username_value.isReadOnly()
    assert page.profile_role_value.isReadOnly()
    assert dialog.username_input.isReadOnly()
    assert dialog.role_input.isReadOnly()
    assert set(dialog.values()) == {
        "Account User",
        "account@example.com",
        "0901234567",
    }


def test_profile_update_sends_no_target_id_role_or_active_value():
    app()
    service = AccountServiceStub()
    actor = session()
    page = SystemPage(
        service,
        actor,
        profile_dialog_factory=AcceptedProfileDialog,
    )
    page.refresh_own_profile()

    assert page.edit_own_profile() is True
    call = next(call for call in service.calls if call[0] == "update_profile")
    assert call == (
        "update_profile",
        actor,
        "Updated Name",
        "updated@example.com",
        "0912345678",
    )
    assert page.profile_full_name_value.text() == "Updated Name"


def test_change_password_dialog_masks_all_fields_and_blocks_mismatch():
    app()
    dialog = ChangePasswordDialog()
    for field in (
        dialog.current_password_input,
        dialog.new_password_input,
        dialog.confirm_password_input,
    ):
        assert field.echoMode() == QLineEdit.EchoMode.Password
    dialog.current_password_input.setText("Current@123")
    dialog.new_password_input.setText("Different@456")
    dialog.confirm_password_input.setText("Mismatch@789")

    with pytest.raises(ValidationError):
        dialog.values()
    dialog._accept_if_valid()
    assert dialog.result() != QDialog.DialogCode.Accepted
    assert "không khớp" in dialog.error_label.text()


def test_valid_password_confirmation_reaches_service_and_fields_are_cleared():
    app()
    service = AccountServiceStub()
    actor = session()
    page = SystemPage(
        service,
        actor,
        change_password_dialog_factory=AcceptedPasswordDialog,
    )
    page.refresh_own_profile()

    assert page.change_own_password() is True
    assert next(call for call in service.calls if call[0] == "password") == (
        "password",
        actor,
        "Current@123",
        "Different@456",
    )
    assert AcceptedPasswordDialog.instance.cleared is True


def test_profile_service_error_is_safe_and_clears_stale_data():
    app()

    class FailingService(AccountServiceStub):
        def get_own_profile(self, actor):
            raise RuntimeError("raw pyodbc secret")

    page = SystemPage(FailingService(), session())
    page.own_profile = profile()

    assert page.refresh_own_profile() is False
    assert page.own_profile is None
    assert "pyodbc" not in page.state_label.text().lower()
    assert "secret" not in page.state_label.text().lower()


def test_account_ui_has_no_sql_repository_or_password_hash_dependency():
    combined = "\n".join(
        inspect.getsource(component)
        for component in (SystemPage, ProfileDialog, ChangePasswordDialog)
    ).lower()

    assert "select " not in combined
    assert "insert " not in combined
    assert "update dbo" not in combined
    assert "repository" not in combined
    assert "password_hash" not in combined
