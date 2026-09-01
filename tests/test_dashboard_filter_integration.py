import os
from datetime import date

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from ui.pages.dashboard_page import DashboardPage
from ui.widgets.dashboard_filter import DashboardFilterWidget


def get_app():
    app = QApplication.instance()
    return app or QApplication([])


class FakeAcademicService:
    def list_school_years(self):
        return [(1, "2026-2027", date(2026, 9, 1), date(2027, 5, 31), True)]

    def list_grades(self):
        return [(6, 6, "Khối 6")]

    def list_active_subjects(self):
        return [(1, "TOAN", "Toán")]

    def list_classes_by_school_year(self, school_year_id):
        return [(1, "6A1", 6, None, "ACTIVE")]


def test_dashboard_page_uses_real_filter_when_service_is_injected():
    get_app()
    page = DashboardPage(academic_service=FakeAcademicService())

    assert isinstance(page.filter_widget, DashboardFilterWidget)

    page.load_filter_options()

    assert page.filter_widget.current_value().school_year_id == 1


def test_dashboard_page_remains_compatible_without_service():
    get_app()
    page = DashboardPage()

    assert page.filter_widget is None
    assert page.filter_placeholder_label is not None
