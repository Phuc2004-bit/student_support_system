import os
from datetime import date
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

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


class FailingEnrollmentService:
    def get_student_history(self, student_id):
        raise RuntimeError("Không đọc được enrollment.")


def test_history_error_is_shown_and_clears_widget(
    monkeypatch,
):
    app()
    shown = []

    monkeypatch.setattr(
        "ui.pages.students_page.QMessageBox.warning",
        lambda *args, **kwargs: shown.append(args),
    )

    page = StudentsPage(
        ListService(),
        enrollment_service=FailingEnrollmentService(),
    )
    page.set_students([row()])
    page.table.selectRow(0)

    assert page.current_enrollment is None
    assert "Không đọc được enrollment." in shown[0][2]


def test_enrollment_active_helper_accepts_enum():
    from models.dto.enrollment import EnrollmentListItem
    from models.enums import EnrollmentStatus
    from ui.pages.students_page import enrollment_is_active

    item = EnrollmentListItem(
        1, "id1", "HS01", "A", 10, "6A1", 6,
        2, "2026-2027", EnrollmentStatus.ACTIVE,
    )

    assert enrollment_is_active(item) is True
