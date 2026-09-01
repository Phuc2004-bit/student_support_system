import os
from datetime import date

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from ui.widgets.dashboard_filter import DashboardFilterWidget


def get_app():
    app = QApplication.instance()
    return app or QApplication([])


class FakeAcademicService:
    def list_school_years(self):
        return [
            (1, "2025-2026", date(2025, 9, 1), date(2026, 5, 31), False),
            (2, "2026-2027", date(2026, 9, 1), date(2027, 5, 31), True),
        ]

    def list_grades(self):
        return [
            (6, 6, "Khối 6"),
            (7, 7, "Khối 7"),
        ]

    def list_active_subjects(self):
        return [
            (1, "TOAN", "Toán"),
            (2, "VAN", "Ngữ văn"),
        ]

    def list_classes_by_school_year(self, school_year_id):
        if school_year_id == 2:
            return [
                (20, "6A1", 6, None, "ACTIVE"),
                (21, "6A2", 6, None, "ACTIVE"),
                (22, "7A1", 7, None, "ACTIVE"),
                (23, "7OLD", 7, None, "INACTIVE"),
            ]
        return [(10, "6B1", 6, None, "ACTIVE")]


def test_load_options_selects_current_school_year():
    get_app()
    widget = DashboardFilterWidget(FakeAcademicService())
    widget.load_options()

    assert widget.current_value().school_year_id == 2
    assert widget.school_year_combo.currentText() == "2026-2027"


def test_optional_filters_start_as_all():
    get_app()
    widget = DashboardFilterWidget(FakeAcademicService())
    widget.load_options()

    value = widget.current_value()
    assert value.grade_id is None
    assert value.class_id is None
    assert value.subject_id is None


def test_grade_filters_classes_and_hides_inactive_class():
    get_app()
    widget = DashboardFilterWidget(FakeAcademicService())
    widget.load_options()

    index = widget.grade_combo.findData(6)
    widget.grade_combo.setCurrentIndex(index)

    texts = [
        widget.class_combo.itemText(i)
        for i in range(widget.class_combo.count())
    ]

    assert texts == ["Tất cả lớp", "6A1", "6A2"]


def test_school_year_change_reloads_classes():
    get_app()
    widget = DashboardFilterWidget(FakeAcademicService())
    widget.load_options()

    index = widget.school_year_combo.findData(1)
    widget.school_year_combo.setCurrentIndex(index)

    texts = [
        widget.class_combo.itemText(i)
        for i in range(widget.class_combo.count())
    ]

    assert texts == ["Tất cả lớp", "6B1"]


def test_filter_signal_emits_current_value():
    get_app()
    widget = DashboardFilterWidget(FakeAcademicService())
    received = []
    widget.filters_changed.connect(received.append)

    widget.load_options()
    widget.subject_combo.setCurrentIndex(
        widget.subject_combo.findData(2)
    )

    assert received
    assert received[-1].subject_id == 2
