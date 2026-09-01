import os
from datetime import date
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QDialog

from models.dto.enrollment import EnrollmentListItem
from models.dto.student_list import StudentListItem
from models.enums import EnrollmentStatus, StudentStatus
from ui.pages.students_page import StudentsPage


def app():
    return QApplication.instance() or QApplication([])


def row():
    return StudentListItem(
        "id1", "HS01", "A", date(2012,1,1),
        "Nam", "6A1", 6, StudentStatus.ACTIVE,
    )


def enrollment():
    return EnrollmentListItem(
        1, "id1", "HS01", "A", 10, "6A1", 6,
        2, "2026-2027", EnrollmentStatus.ACTIVE,
    )


class ListService:
    def list_students(self, filters=None):
        return [row()]


class EnrollmentService:
    def __init__(self):
        self.args = None

    def get_student_history(self, student_id):
        return [enrollment()]

    def transfer_student(
        self, student_id, class_id, transfer_date
    ):
        self.args = (
            student_id, class_id, transfer_date
        )
        return object()


class Dialog:
    DialogCode = QDialog.DialogCode
    last_kwargs = None

    def __init__(self, **kwargs):
        Dialog.last_kwargs = kwargs

    def load_options(self):
        pass

    def exec(self):
        return QDialog.DialogCode.Accepted

    def selected_class_id(self):
        return 11

    def action_date(self):
        return date(2026, 9, 8)


def test_transfer_calls_service_with_new_class(
    monkeypatch,
):
    app()
    service = EnrollmentService()
    page = StudentsPage(
        ListService(),
        enrollment_service=service,
        enrollment_dialog_factory=Dialog,
    )
    page.set_students([row()])
    page.table.selectRow(0)

    monkeypatch.setattr(
        "ui.pages.students_page.QMessageBox.information",
        lambda *a, **k: None,
    )

    assert page._transfer_selected_student() is True
    assert service.args == (
        "id1", 11, date(2026, 9, 8)
    )
    assert Dialog.last_kwargs["current_class_id"] == 10


def test_transfer_requires_active_enrollment():
    app()
    service = EnrollmentService()
    page = StudentsPage(
        ListService(),
        enrollment_service=service,
        enrollment_dialog_factory=Dialog,
    )
    page.set_students([row()])
    page.table.selectRow(0)
    page._clear_current_enrollment()

    assert page._transfer_selected_student() is False
