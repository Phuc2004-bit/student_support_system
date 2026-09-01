import os
from datetime import date
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QDialog

from models.dto.student_list import StudentListItem
from models.enums import StudentStatus
from ui.pages.students_page import StudentsPage


def app():
    return QApplication.instance() or QApplication([])


def row():
    return StudentListItem(
        "id1", "HS01", "A", date(2012,1,1),
        "Nam", None, None, StudentStatus.ACTIVE,
    )


class ListService:
    def list_students(self, filters=None):
        return [row()]


class EnrollmentService:
    def __init__(self):
        self.args = None

    def get_student_history(self, student_id):
        return []

    def enroll_student(
        self, student_id, class_id, enrollment_date
    ):
        self.args = (
            student_id, class_id, enrollment_date
        )
        return object()


class Dialog:
    DialogCode = QDialog.DialogCode

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def load_options(self):
        pass

    def exec(self):
        return QDialog.DialogCode.Accepted

    def selected_class_id(self):
        return 10

    def action_date(self):
        return date(2026, 9, 7)


def test_assign_calls_enrollment_service_and_refreshes(
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

    saved = []
    page.enrollment_saved.connect(saved.append)

    assert page._assign_selected_student() is True
    assert service.args == (
        "id1", 10, date(2026, 9, 7)
    )
    assert saved == ["id1"]


def test_assign_without_selected_student_returns_false():
    app()
    page = StudentsPage(
        ListService(),
        enrollment_service=EnrollmentService(),
        enrollment_dialog_factory=Dialog,
    )
    page.set_students([row()])

    assert page._assign_selected_student() is False
