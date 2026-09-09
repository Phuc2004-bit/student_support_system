from datetime import date, datetime
from decimal import Decimal
import inspect
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from matplotlib.colors import to_hex
from PySide6.QtWidgets import QApplication, QLineEdit

from app_context import AppContext
from models.dto import InterventionDetail, UserSession
from models.dto.score_import import ScoreImportContext, ScoreImportPreview
from models.enums import InterventionStatus, UserRole
from services.permission_service import PermissionService
from ui import theme
from ui.dialogs.catalog_dialogs import AssessmentDialog, SchoolYearDialog
from ui.dialogs.change_password_dialog import ChangePasswordDialog
from ui.dialogs.enrollment_dialog import EnrollmentDialog
from ui.dialogs.intervention_detail_dialog import InterventionDetailDialog
from ui.dialogs.intervention_plan_dialog import InterventionPlanDialog
from ui.dialogs.intervention_review_dialog import InterventionReviewDialog
from ui.dialogs.login_dialog import LoginDialog
from ui.dialogs.score_import_preview_dialog import ScoreImportPreviewDialog
from ui.dialogs.student_form_dialog import StudentFormDialog
from ui.dialogs.student_profile_dialog import StudentProfileDialog
from ui.dialogs.user_dialog import UserDialog
from ui.main_window import MainWindow
from ui.pages.catalog_page import CatalogPage
from ui.pages.dashboard_page import DashboardPage
from ui.pages.reports_page import ReportsPage
from ui.pages.scores_page import ScoresPage
from ui.pages.students_page import StudentsPage
from ui.pages.support_page import SupportPage
from ui.pages.system_page import SystemPage
from ui.widgets.dashboard_charts import DashboardBarChart, DashboardDonutChart


def app():
    return QApplication.instance() or QApplication([])


def context(role=UserRole.ADMIN):
    return AppContext(
        db=object(), auth_service=object(), permission_service=PermissionService(),
        session=UserSession(1, "actor", "Nguyễn Minh An", role),
    )


def detail(status=InterventionStatus.DETECTED):
    now = datetime(2042, 1, 2, 3, 4, 5)
    return InterventionDetail(
        1, 2, "student-id", "HS001", "Nguyễn An", "6A", 3, "Toán",
        4, Decimal("3.00"), None, None, date(2042, 1, 1), None, status,
        None, None, now, now, (), 6, 5, "2041-2042", "MATH", "Kiểm tra",
    )


def empty_preview():
    return ScoreImportPreview(
        ScoreImportContext(1, "2041-2042", 2, "6A", 3, "Toán", 4, "Kiểm tra"),
        (),
    )


def test_admin_main_window_constructs_with_all_navigation_entries():
    app()
    window = MainWindow(context())
    assert tuple(window.PAGE_TITLES) == tuple(window.page_stack._pages)
    assert all(not window.sidebar.button(key).isHidden() for key in window.PAGE_TITLES)
    window.close()


def test_teacher_main_window_constructs_without_permission_visual_leak():
    app()
    window = MainWindow(context(UserRole.TEACHER))
    assert window.sidebar.button("catalogs").isHidden()
    assert window.can_navigate_to("catalogs") is False
    assert not window.sidebar.button("system").isHidden()
    window.close()


def test_all_seven_admin_pages_are_real_widgets():
    app()
    window = MainWindow(context())
    expected = (DashboardPage, StudentsPage, ScoresPage, SupportPage, ReportsPage, CatalogPage, SystemPage)
    assert tuple(type(window.page_stack.page(key)) for key in window.PAGE_TITLES) == expected
    window.close()


def test_teacher_allowed_pages_construct_and_remain_navigable():
    app()
    window = MainWindow(context(UserRole.TEACHER))
    allowed = ("dashboard", "students", "scores", "support", "reports", "system")
    assert all(window.can_navigate_to(key) for key in allowed)
    window.close()


def test_catalog_is_hidden_and_programmatic_navigation_is_blocked_for_teacher():
    app()
    window = MainWindow(context(UserRole.TEACHER))
    before = window.page_stack.current_key
    with pytest.raises(PermissionError):
        window.navigate_to("catalogs")
    assert window.page_stack.current_key == before
    window.close()


def test_teacher_system_page_contains_self_profile_only():
    app()
    page = SystemPage(session=context(UserRole.TEACHER).session)
    assert page.tabs.count() == 1
    assert page.tabs.tabText(0) == "Tài khoản của tôi"
    assert page.users_tab.isHidden()


def test_login_dialog_uses_dark_brand_card_and_primary_action():
    app()
    dialog = LoginDialog(object())
    assert dialog.objectName() == "loginDialog"
    assert dialog.form_card.objectName() == "loginCard"
    assert dialog.login_button.property("variant") == "primary"
    assert theme.APP_BACKGROUND in dialog.styleSheet()


def test_login_has_password_masking_focus_and_no_registration_action():
    app()
    dialog = LoginDialog(object())
    assert dialog.password_input.echoMode() == QLineEdit.EchoMode.Password
    assert dialog.login_button.isDefault()
    assert not any("đăng ký" in button.text().lower() for button in dialog.findChildren(type(dialog.login_button)))


def test_student_enrollment_profile_and_assessment_dialogs_construct():
    app()
    dialogs = (
        StudentFormDialog(), EnrollmentDialog(), StudentProfileDialog("student-id", object()),
        AssessmentDialog([], []), SchoolYearDialog(),
    )
    assert all(dialog.styleSheet() for dialog in dialogs)
    assert dialogs[2].tabs.count() == 4


def test_import_user_and_password_dialogs_construct_with_consistent_theme():
    app()
    dialogs = (ScoreImportPreviewDialog(empty_preview()), UserDialog(), ChangePasswordDialog())
    assert all(theme.APP_BACKGROUND in dialog.styleSheet() for dialog in dialogs)
    password = dialogs[-1]
    assert all(field.echoMode() == QLineEdit.EchoMode.Password for field in (
        password.current_password_input, password.new_password_input, password.confirm_password_input,
    ))


def test_support_detail_plan_and_review_dialogs_construct():
    app()
    value = detail()
    dialogs = (
        InterventionDetailDialog(1, object()),
        InterventionPlanDialog(value, object(), object()),
        InterventionReviewDialog(value, object(), object()),
    )
    assert all(theme.APP_BACKGROUND in dialog.styleSheet() for dialog in dialogs)


def test_central_theme_covers_popups_message_boxes_calendars_and_tooltips():
    style = theme.main_window_stylesheet()
    for selector in ("QMenu", "QToolTip", "QMessageBox", "QCalendarWidget", "QTableCornerButton"):
        assert selector in style


def test_central_theme_covers_input_focus_disabled_pressed_and_scrollbars():
    combined = theme.main_window_stylesheet() + theme.dialog_stylesheet()
    for selector in ("QPlainTextEdit", "QDoubleSpinBox", ":focus", ":disabled", ":pressed", "QScrollBar:horizontal"):
        assert selector in combined


def test_button_system_has_primary_secondary_danger_and_navigation_selectors():
    combined = theme.main_window_stylesheet() + theme.dialog_stylesheet()
    assert 'variant="primary"' in combined
    assert 'variant="danger"' in combined
    assert 'navItem="true"' in combined
    assert "QDialog QPushButton" in combined


def test_all_charts_keep_dark_figure_axes_and_canvas():
    app()
    for chart in (DashboardBarChart(), DashboardDonutChart()):
        assert to_hex(chart.figure.get_facecolor()).upper() == theme.SURFACE
        assert to_hex(chart.axes.get_facecolor()).upper() == theme.SURFACE
        assert theme.SURFACE in chart.canvas.styleSheet()


def test_support_and_report_status_badges_share_one_palette():
    for status in InterventionStatus:
        foreground, background = theme.status_badge_colors(status)
        assert foreground.startswith("#") and background.startswith("#")
    assert theme.status_badge_colors("COMPLETED") == (theme.SUCCESS, theme.SUCCESS_SUBTLE)


def test_catalog_system_and_assessment_statuses_use_central_palette():
    assert theme.status_badge_colors("ACTIVE") == (theme.SUCCESS, theme.SUCCESS_SUBTLE)
    assert theme.status_badge_colors("LOCKED") == (theme.WARNING, theme.WARNING_SUBTLE)
    assert theme.status_badge_colors("CANCELLED") == (
        theme.TEXT_SECONDARY, theme.SIDEBAR_BACKGROUND,
    )


def test_completed_intervention_has_no_manual_complete_action():
    app()
    dialog = InterventionDetailDialog(1, object())
    dialog.detail = detail(InterventionStatus.COMPLETED)
    dialog._render_detail(dialog.detail)
    button_text = " ".join(button.text().lower() for button in dialog.findChildren(type(dialog.plan_button)))
    assert "hoàn thành" not in button_text


def test_locked_assessment_remains_a_saved_non_active_status():
    app()
    dialog = AssessmentDialog([], [])
    values = [str(getattr(dialog.status_combo.itemData(i), "value", dialog.status_combo.itemData(i)))
              for i in range(dialog.status_combo.count())]
    assert values == ["ACTIVE", "LOCKED", "CANCELLED"]


def test_empty_states_construct_without_dummy_data_or_white_chart():
    app()
    assert CatalogPage().school_year_table.rowCount() == 0
    assert SystemPage(session=context().session).user_table.rowCount() == 0
    assert ScoreImportPreviewDialog(empty_preview()).table.rowCount() == 0
    assert DashboardBarChart().axes.axison is False


def test_logout_invalidates_old_window_navigation_without_changing_session_logic():
    app()
    app_context = context()
    window = MainWindow(app_context)
    window.sidebar.logout_button.click()
    assert app_context.session is None
    assert window.can_navigate_to("dashboard") is False
    window.close()


def test_ui_sources_do_not_add_registration_sql_hash_or_business_rules():
    modules = (LoginDialog, MainWindow, CatalogPage, SystemPage)
    source = "\n".join(inspect.getsource(inspect.getmodule(component)) for component in modules).lower()
    for forbidden in ("select ", "insert ", "password_hash", "create_account"):
        assert forbidden not in source
