from datetime import datetime
import inspect
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QDialogButtonBox, QLineEdit

from models.dto import UserListItem, UserSession
from models.enums import UserRole
from ui.dialogs.catalog_dialogs import (
    AssessmentDialog,
    ClassDialog,
    GradeDialog,
    SchoolYearDialog,
    SubjectDialog,
    SupportRuleDialog,
)
from ui.dialogs.change_password_dialog import ChangePasswordDialog
from ui.dialogs.profile_dialog import ProfileDialog
from ui.dialogs.user_dialog import UserDialog
from ui.pages.catalog_page import CatalogPage
from ui.pages.system_page import SystemPage
from ui.theme import APP_BACKGROUND, PRIMARY, SURFACE, catalog_system_stylesheet


def app():
    return QApplication.instance() or QApplication([])


def session(role=UserRole.ADMIN):
    return UserSession(1, "admin", "System Admin", role)


def user(role=UserRole.ADMIN, active=True):
    now = datetime(2042, 1, 2, 3, 4, 5)
    return UserListItem(
        1, "admin", "Nguyen Van Admin", role,
        "admin@example.com", "0901234567", active, now, now,
    )


def test_catalog_page_uses_shared_dark_design_tokens_and_category_navigation():
    app()
    page = CatalogPage()
    assert APP_BACKGROUND in page.styleSheet()
    assert SURFACE in page.styleSheet()
    assert PRIMARY in page.styleSheet()
    assert [page.tabs.tabText(i) for i in range(page.tabs.count())] == [
        "Năm học", "Khối", "Lớp"
    ]
    assert [page.advanced_tabs.tabText(i) for i in range(page.advanced_tabs.count())] == [
        "Môn học", "Bài đánh giá", "Ngưỡng bổ trợ"
    ]


def test_catalog_primary_actions_are_distinct_without_inventing_delete():
    app()
    page = CatalogPage()
    add_buttons = (
        page.add_school_year_button, page.add_grade_button, page.add_class_button,
        page.add_subject_button, page.add_assessment_button, page.add_rule_button,
    )
    assert all(button.property("variant") == "primary" for button in add_buttons)
    assert not any("xóa" in button.text().lower() for button in page.findChildren(type(add_buttons[0])))


def test_catalog_tables_are_compact_read_only_and_have_explicit_empty_states():
    app()
    page = CatalogPage()
    tables = (
        page.school_year_table, page.grade_table, page.class_table,
        page.subject_table, page.assessment_table, page.rule_table,
    )
    assert all(not table.showGrid() for table in tables)
    assert all(table.verticalHeader().defaultSectionSize() == 38 for table in tables)
    assert len(page._empty_labels) == 6
    page._render_school_years()
    assert not page._empty_labels[page.school_year_table].isHidden()


def test_support_rule_explanation_is_generic_and_not_a_hard_coded_threshold():
    app()
    page = CatalogPage()
    text = page.rule_explanation_label.text().lower()
    assert "điểm thấp hơn ngưỡng" in text
    assert "3.5" not in text


@pytest.mark.parametrize(
    "dialog",
    [
        lambda: SchoolYearDialog(),
        lambda: GradeDialog(),
        lambda: ClassDialog([], []),
        lambda: SubjectDialog(),
        lambda: AssessmentDialog([], []),
        lambda: SupportRuleDialog([], []),
    ],
)
def test_catalog_dialogs_share_modern_card_and_primary_action(dialog):
    app()
    instance = dialog()
    assert instance.styleSheet()
    assert instance.form_card.property("dialogCard") is True
    save = instance.button_box.button(QDialogButtonBox.StandardButton.Save)
    assert save.property("variant") == "primary"


def test_catalog_dialogs_preserve_existing_fields_and_dependencies():
    app()
    class_dialog = ClassDialog([], [])
    assessment_dialog = AssessmentDialog([], [])
    rule_dialog = SupportRuleDialog([], [])
    assert class_dialog.school_year_combo.count() == 0
    assert class_dialog.grade_combo.count() == 0
    assert assessment_dialog.subject_combo.count() == 0
    assert rule_dialog.threshold_input.maxLength() >= 1


def test_system_page_separates_self_profile_and_admin_user_management():
    app()
    page = SystemPage(session=session(UserRole.ADMIN))
    assert [page.tabs.tabText(i) for i in range(page.tabs.count())] == [
        "Tài khoản của tôi", "Người dùng"
    ]
    assert page.profile_card.objectName() == "profileCard"
    assert page.add_button.property("variant") == "primary"


def test_teacher_sees_only_self_profile_according_to_existing_permission():
    app()
    page = SystemPage(session=session(UserRole.TEACHER))
    assert page.tabs.count() == 1
    assert page.tabs.tabText(0) == "Tài khoản của tôi"


def test_profile_card_renders_initials_and_safe_identity_fields():
    app()
    page = SystemPage(session=session())
    page.own_profile = user()
    page._render_own_profile()
    assert page.profile_avatar_label.text() == "VA"
    assert page.profile_name_label.text() == "Nguyen Van Admin"
    assert page.profile_username_value.isReadOnly()
    assert page.profile_role_value.isReadOnly()


def test_user_table_is_compact_and_empty_state_is_explicit():
    app()
    page = SystemPage(session=session())
    page.users = ()
    page._render_users()
    assert not page.user_table.showGrid()
    assert page.user_table.verticalHeader().defaultSectionSize() == 40
    assert not page.users_empty_label.isHidden()
    assert all("password" not in page.user_table.horizontalHeaderItem(i).text().lower()
               for i in range(page.user_table.columnCount()))


def test_user_dialog_keeps_password_masked_and_edit_identity_locked():
    app()
    create_dialog = UserDialog()
    edit_dialog = UserDialog(user())
    assert create_dialog.password_input.echoMode() == QLineEdit.EchoMode.Password
    assert not edit_dialog.username_input.isEnabled()
    assert edit_dialog.password_input.isHidden()
    assert edit_dialog.active_checkbox.isEnabled() is False
    assert create_dialog.save_button.property("variant") == "primary"


def test_profile_and_password_dialogs_keep_security_fields_and_modern_shell():
    app()
    profile_dialog = ProfileDialog(user())
    password_dialog = ChangePasswordDialog()
    assert profile_dialog.username_input.isReadOnly()
    assert profile_dialog.role_input.isReadOnly()
    assert profile_dialog.form_card.property("dialogCard") is True
    assert password_dialog.form_card.property("dialogCard") is True
    assert all(
        field.echoMode() == QLineEdit.EchoMode.Password
        for field in (
            password_dialog.current_password_input,
            password_dialog.new_password_input,
            password_dialog.confirm_password_input,
        )
    )


def test_catalog_system_stylesheet_is_scoped_and_uses_shared_tokens():
    style = catalog_system_stylesheet()
    assert "QWidget#catalogPage" in style
    assert "QWidget#systemPage" in style
    assert APP_BACKGROUND in style and PRIMARY in style and SURFACE in style


def test_step_16_6_ui_has_no_sql_repository_hash_or_fixed_threshold_dependency():
    modules = (
        inspect.getmodule(CatalogPage), inspect.getmodule(SystemPage),
        inspect.getmodule(UserDialog), inspect.getmodule(ProfileDialog),
        inspect.getmodule(ChangePasswordDialog),
    )
    source = "\n".join(inspect.getsource(module) for module in modules).lower()
    for forbidden in ("select ", "insert ", "update dbo", "delete ", "password_hash"):
        assert forbidden not in source
    assert "3.5" not in source
