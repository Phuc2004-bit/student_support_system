from datetime import date, datetime
import inspect
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from app_context import AppContext
from bootstrap import build_app_context
from models.dto import Grade, SchoolYear, Subject, UserListItem, UserSession
from models.dto.report_dto import SupportReportData, SupportReportSummary
from models.enums import UserRole
from services.academic_service import AcademicService
from services.permission_service import PermissionService
from services.report_service import ReportService
from services.user_service import UserService
from ui.main_window import MainWindow
from ui.pages.catalog_page import CatalogPage
from ui.pages.placeholder_page import PlaceholderPage
from ui.pages.reports_page import ReportsPage
from ui.pages.system_page import SystemPage


NOW = datetime(2042, 3, 4, 5, 6, 7)


def app():
    return QApplication.instance() or QApplication([])


def session(role=UserRole.ADMIN):
    return UserSession(
        1 if role == UserRole.ADMIN else 2,
        "admin" if role == UserRole.ADMIN else "teacher",
        "Actor",
        role,
    )


class AcademicStub:
    def __init__(self):
        self.reads = []
        self.writes = []

    def list_school_years(self):
        self.reads.append("years")
        return [(1, "2041-2042", None, None, True)]

    def list_grades(self):
        self.reads.append("grades")
        return [(6, 6, "Khối 6")]

    def list_classes_by_school_year(self, school_year_id):
        self.reads.append(("classes", school_year_id))
        return [(61, "6A1", 6, None, True)]

    def list_active_subjects(self):
        self.reads.append("subjects")
        return [(11, "M1", "Môn 1")]

    def list_catalog_school_years(self):
        self.reads.append("catalog_years")
        return [SchoolYear(1, "2041-2042", date(2041, 9, 1), date(2042, 5, 31), True)]

    def list_catalog_grades(self):
        self.reads.append("catalog_grades")
        return [Grade(6, 6, "Khối 6")]

    def list_catalog_classes(self, school_year_id, grade_id=None):
        self.reads.append(("catalog_classes", school_year_id, grade_id))
        return []

    def list_catalog_subjects(self):
        self.reads.append("catalog_subjects")
        return [Subject(11, "M1", "Môn 1", True)]

    def list_assessments(self, school_year_id, subject_id=None, **_filters):
        self.reads.append(("assessments", school_year_id, subject_id))
        return []

    def list_catalog_support_rules(self, school_year_id, subject_id=None):
        self.reads.append(("rules", school_year_id, subject_id))
        return []


class ReportStub:
    def __init__(self):
        self.reads = []
        self.writes = []

    def get_support_report(self, **filters):
        self.reads.append(filters)
        return SupportReportData(SupportReportSummary(0, 0, 0, 0, 0, 0, 0), ())


class UserStub:
    def __init__(self, actor):
        self.actor = actor
        self.reads = []
        self.writes = []
        self.value = UserListItem(
            actor.user_id,
            actor.username,
            actor.full_name,
            actor.role,
            None,
            None,
            True,
            NOW,
            NOW,
        )

    def get_own_profile(self, actor):
        self.reads.append(("profile", actor))
        return self.value

    def admin_list_users(self, actor, search=None):
        self.reads.append(("users", actor, search))
        return [self.value]


def make_context(role=UserRole.ADMIN, permission_service=None):
    actor = session(role)
    return AppContext(
        db=object(),
        auth_service=object(),
        permission_service=permission_service or PermissionService(),
        session=actor,
        academic_service=AcademicStub(),
        report_service=ReportStub(),
        user_service=UserStub(actor),
    )


def test_bootstrap_reuses_one_database_for_required_wiring_services():
    context = build_app_context()

    assert isinstance(context.academic_service, AcademicService)
    assert isinstance(context.report_service, ReportService)
    assert isinstance(context.user_service, UserService)
    assert context.academic_service.db is context.db
    assert context.report_service.db is context.db
    assert context.user_service.db is context.db


def test_main_window_registers_three_real_pages_with_exact_dependencies():
    app()
    context = make_context()
    window = MainWindow(context)

    reports = window.pages["reports"]
    catalogs = window.pages["catalogs"]
    system = window.pages["system"]
    assert isinstance(reports, ReportsPage)
    assert isinstance(catalogs, CatalogPage)
    assert isinstance(system, SystemPage)
    assert not any(isinstance(page, PlaceholderPage) for page in (reports, catalogs, system))
    assert reports.academic_service is context.academic_service
    assert reports.report_service is context.report_service
    assert catalogs.academic_service is context.academic_service
    assert system.user_service is context.user_service
    assert system.session is context.session
    assert system.permission_service is context.permission_service


@pytest.mark.parametrize("key", ["reports", "catalogs", "system"])
def test_admin_can_navigate_to_integrated_pages(key):
    app()
    window = MainWindow(make_context())

    assert window.can_navigate_to(key) is True
    window.navigate_to(key)
    assert window.page_stack.current_key == key
    assert window.sidebar.current_key == key


def test_admin_navigation_initializes_all_pages_without_writes_or_export():
    app()
    context = make_context()
    window = MainWindow(context)

    window.navigate_to("reports")
    window.navigate_to("catalogs")
    window.navigate_to("system")

    assert context.report_service.reads
    assert "catalog_years" in context.academic_service.reads
    assert ("profile", context.session) in context.user_service.reads
    assert any(read[0] == "users" for read in context.user_service.reads if isinstance(read, tuple))
    assert context.academic_service.writes == []
    assert context.report_service.writes == []
    assert context.user_service.writes == []
    assert "ReportExportService" not in inspect.getsource(MainWindow)


def test_teacher_can_open_reports_and_system_but_catalog_is_blocked():
    app()
    context = make_context(UserRole.TEACHER)
    window = MainWindow(context)

    assert window.can_navigate_to("reports") is True
    assert window.can_navigate_to("system") is True
    assert window.can_navigate_to("catalogs") is False
    assert not window.sidebar.button("reports").isHidden()
    assert not window.sidebar.button("system").isHidden()
    assert window.sidebar.button("catalogs").isHidden()
    window.navigate_to("reports")
    window.navigate_to("system")
    with pytest.raises(PermissionError):
        window.navigate_to("catalogs")


def test_teacher_system_loads_own_profile_without_user_management():
    app()
    context = make_context(UserRole.TEACHER)
    window = MainWindow(context)
    page = window.pages["system"]

    window.navigate_to("system")

    assert page.tabs.count() == 1
    assert page.tabs.tabText(0) == "Tài khoản của tôi"
    assert page.own_profile.user_id == context.session.user_id
    assert context.user_service.reads == [("profile", context.session)]


def test_custom_permission_cannot_be_bypassed_programmatically():
    class DenyCatalog(PermissionService):
        @staticmethod
        def can_manage_catalogs(_session):
            return False

    app()
    window = MainWindow(make_context(UserRole.ADMIN, DenyCatalog()))

    assert window.sidebar.button("catalogs").isHidden()
    with pytest.raises(PermissionError):
        window.navigate_to("catalogs")
    assert window.page_stack.current_key == "dashboard"


def test_invalid_session_still_cannot_open_main_window():
    app()
    context = make_context()
    context.clear_session()

    with pytest.raises(PermissionError):
        MainWindow(context)
