from __future__ import annotations

import os
from datetime import date

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from matplotlib.colors import to_hex
from PySide6.QtWidgets import QApplication, QHBoxLayout

from app_context import AppContext
from models.dto import UserSession
from models.dto.dashboard_dto import DashboardData, DashboardSummary
from models.enums import UserRole
from services.permission_service import PermissionService
from ui import theme
from ui.main_window import MainWindow
from ui.pages.dashboard_page import DashboardPage
from ui.widgets.dashboard_charts import DashboardBarChart, DashboardDonutChart
from ui.widgets.sidebar import Sidebar


def app() -> QApplication:
    return QApplication.instance() or QApplication([])


def session(role: UserRole) -> UserSession:
    return UserSession(1, "user", "Nguyễn Minh An", role)


def context(role: UserRole) -> AppContext:
    return AppContext(
        db=object(),
        auth_service=object(),
        permission_service=PermissionService(),
        session=session(role),
    )


def test_dark_design_tokens_and_stylesheet_are_centralized():
    colors = (
        theme.APP_BACKGROUND,
        theme.SIDEBAR_BACKGROUND,
        theme.SURFACE,
        theme.BORDER,
        theme.PRIMARY,
        theme.TEXT_PRIMARY,
    )

    assert all(color.startswith("#") and len(color) == 7 for color in colors)
    stylesheet = theme.main_window_stylesheet()
    assert "QMainWindow#mainWindow" in stylesheet
    assert "navItem" in stylesheet
    assert "variant=\"primary\"" in stylesheet
    assert "QTableWidget" in stylesheet


def test_main_window_uses_sidebar_then_header_content_shell_and_stable_keys():
    app()
    window = MainWindow(context(UserRole.ADMIN))

    assert isinstance(window.central_widget.layout(), QHBoxLayout)
    assert window.central_widget.layout().itemAt(0).widget() is window.sidebar
    assert window.central_widget.layout().itemAt(1).widget() is window.body_widget
    assert window.body_widget.layout().itemAt(0).widget() is window.topbar
    assert window.body_widget.layout().itemAt(1).widget() is window.page_stack
    assert window.minimumWidth() <= 1366
    assert window.minimumHeight() <= 768
    assert tuple(window.PAGE_TITLES) == (
        "dashboard",
        "students",
        "scores",
        "support",
        "reports",
        "catalogs",
        "system",
    )
    assert theme.APP_BACKGROUND in window.styleSheet()
    window.close()


def test_sidebar_has_grouped_navigation_and_session_user_block():
    app()
    sidebar = Sidebar(session=session(UserRole.ADMIN))

    assert tuple(sidebar.section_labels) == ("TỔNG QUAN", "QUẢN LÝ", "QUẢN TRỊ")
    assert sidebar.user_label.text() == "Nguyễn Minh An"
    assert sidebar.role_label.text() == "Quản trị viên"
    assert sidebar.avatar_label.text() == "MA"
    assert sidebar.logout_button.property("variant") == "danger"
    assert all(sidebar.button(item.key).property("navItem") for item in sidebar.ITEMS)


def test_admin_and_teacher_navigation_visibility_still_uses_existing_policy():
    app()
    admin = MainWindow(context(UserRole.ADMIN))
    teacher = MainWindow(context(UserRole.TEACHER))

    assert all(not admin.sidebar.button(key).isHidden() for key in admin.PAGE_TITLES)
    assert teacher.sidebar.button("catalogs").isHidden()
    assert not teacher.sidebar.button("system").isHidden()
    assert teacher.sidebar.role_label.text() == "Giáo viên"
    assert teacher.can_navigate_to("catalogs") is False
    assert teacher.can_navigate_to("dashboard") is True
    admin.close()
    teacher.close()


def test_dashboard_sections_are_ordered_and_kpis_prioritize_four_columns():
    app()
    page = DashboardPage()
    layout = page.scroll_contents.layout()

    assert layout.indexOf(page.kpi_frame) >= 0
    assert layout.indexOf(page.filter_frame) >= 0
    assert layout.indexOf(page.chart_frame) >= 0
    assert layout.indexOf(page.attention_frame) >= 0
    assert layout.indexOf(page.kpi_frame) < layout.indexOf(page.filter_frame)
    assert layout.indexOf(page.filter_frame) < layout.indexOf(page.chart_frame)
    assert layout.indexOf(page.chart_frame) < layout.indexOf(page.attention_frame)

    main_keys = (
        "total_students",
        "needs_support_count",
        "in_progress_count",
        "completed_count",
    )
    for column, key in enumerate(main_keys):
        index = page.kpi_grid_layout.indexOf(page.kpi_cards[key])
        row, actual_column, _, _ = page.kpi_grid_layout.getItemPosition(index)
        assert (row, actual_column) == (0, column)


class AcademicStub:
    def list_school_years(self):
        return [(1, "2026-2027", date(2026, 9, 1), date(2027, 5, 31), True)]

    def list_grades(self):
        return []

    def list_active_subjects(self):
        return []

    def list_classes_by_school_year(self, school_year_id):
        return []


class DashboardStub:
    def __init__(self):
        self.calls = []

    def get_dashboard(self, **filters):
        self.calls.append(filters)
        return DashboardData(
            summary=DashboardSummary(12, 3, 2, 1, 1, 1),
            status_breakdown=(),
            attention_items=(),
        )


def test_dashboard_filter_refresh_and_real_dto_binding_are_unchanged():
    app()
    service = DashboardStub()
    page = DashboardPage(AcademicStub(), service)

    page.initialize_dashboard()

    assert service.calls == [
        {
            "school_year_id": 1,
            "grade_id": None,
            "class_id": None,
            "subject_id": None,
        }
    ]
    assert page.kpi_cards["total_students"].value == 12
    assert page.kpi_cards["completed_count"].value == 1
    assert page.attention_table.empty_label.isVisibleTo(page)


def test_chart_surfaces_and_empty_states_are_dark():
    app()
    charts = (DashboardBarChart(), DashboardDonutChart())

    for chart in charts:
        assert to_hex(chart.figure.get_facecolor()).upper() == theme.SURFACE
        assert to_hex(chart.axes.get_facecolor()).upper() == theme.SURFACE
        assert chart.axes.axison is False
        assert chart.axes.texts
        assert chart.axes.texts[0].get_color().upper() == theme.TEXT_SECONDARY


def test_sidebar_logout_preserves_session_invalidation_and_stale_guard():
    app()
    app_context = context(UserRole.ADMIN)
    window = MainWindow(app_context)
    emitted = []
    window.logout_requested.connect(lambda: emitted.append(True))

    window.sidebar.logout_button.click()

    assert emitted == [True]
    assert app_context.session is None
    assert window.can_navigate_to("dashboard") is False
