import os
from datetime import date

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from models.dto.student_list import StudentListItem
from models.enums import StudentStatus
from ui.pages.students_page import StudentsPage


def app():
    return QApplication.instance() or QApplication([])


class ProfileService:
    pass


class Dialog:
    last_kwargs = None

    def __init__(self, **kwargs):
        Dialog.last_kwargs = kwargs
        self.loaded = False

    def load_profile(self):
        self.loaded = True

    def exec(self):
        return 0


def test_selected_student_can_open_profile_dialog():
    app()
    page = StudentsPage(
        student_profile_service=ProfileService(),
        profile_dialog_factory=Dialog,
    )
    page.set_students((StudentListItem(
        "student-1", "HS001", "Nguyễn Văn A", date(2012, 1, 2),
        "Nam", "6A1", 6, StudentStatus.ACTIVE,
    ),))
    page.table.selectRow(0)

    assert page.profile_button.isEnabled() is True
    assert page._show_selected_profile() is True
    assert Dialog.last_kwargs["student_id"] == "student-1"
    assert isinstance(Dialog.last_kwargs["profile_service"], ProfileService)
