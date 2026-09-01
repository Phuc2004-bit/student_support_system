import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from ui.pages.students_page import StudentsPage


def app():
    return QApplication.instance() or QApplication([])


def test_filter_change_without_service_does_not_crash():
    app()
    page = StudentsPage()

    page.filter_widget.search_input.setText("HS01")
    page.filter_widget._timer.stop()
    page.filter_widget._emit()

    assert page.table.rowCount() == 0
    assert page.count_label.text() == "0 học sinh"


def test_refresh_without_service_returns_false():
    app()
    page = StudentsPage()

    assert page.refresh_students() is False
