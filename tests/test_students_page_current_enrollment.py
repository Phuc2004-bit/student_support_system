import os
from datetime import date
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from models.dto.enrollment import EnrollmentListItem
from models.dto.student_list import StudentListItem
from models.enums import EnrollmentStatus, StudentStatus
from ui.pages.students_page import StudentsPage


def app():
    return QApplication.instance() or QApplication([])


def row():
    return StudentListItem(
        "id1", "HS01", "A", date(2012, 1, 1),
        "Nam", "6A1", 6, StudentStatus.ACTIVE,
    )


def enrollment():
    return EnrollmentListItem(
        1, "id1", "HS01", "A", 10, "6A1", 6,
        2, "2026-2027", EnrollmentStatus.ACTIVE,
    )


def transferred_enrollment():
    return EnrollmentListItem(
        2, "id1", "HS01", "A", 9, "6A0", 6,
        1, "2025-2026", EnrollmentStatus.TRANSFERRED,
    )


class ListService:
    def list_students(self, filters=None):
        return [row()]


class EnrollmentService:
    def get_student_history(self, student_id):
        assert student_id == "id1"
        return [transferred_enrollment(), enrollment()]


def test_selection_loads_current_enrollment():
    app()
    page = StudentsPage(
        ListService(),
        enrollment_service=EnrollmentService(),
    )
    page.set_students([row()])
    page.table.selectRow(0)

    assert page.current_enrollment.class_name == "6A1"
    assert (
        page.current_enrollment_widget.class_label.text()
        == "6A1"
    )
    assert page.enrollment_history == (
        transferred_enrollment(), enrollment(),
    )
    assert page.enrollment_history_widget.table.rowCount() == 2
    assert (
        page.enrollment_history_widget.table.item(0, 3).text()
        == "Đã chuyển lớp"
    )
    assert (
        page.enrollment_history_widget.table.item(1, 3).text()
        == "Đang học"
    )


def test_no_selection_clears_current_enrollment():
    app()
    page = StudentsPage(
        ListService(),
        enrollment_service=EnrollmentService(),
    )
    page.set_students([row()])

    assert page.current_enrollment is None
    assert page.enrollment_history == ()
    assert page.enrollment_history_widget.table.rowCount() == 0
