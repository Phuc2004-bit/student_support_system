import os
from datetime import date, datetime

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from models.dto import Student
from models.enums import StudentStatus
from ui.dialogs.student_form_dialog import StudentFormDialog


def app():
    return QApplication.instance() or QApplication([])


def make_student():
    now = datetime.now()
    return Student(
        student_id="id",
        student_code="HS01",
        full_name="A",
        date_of_birth=date(2012, 1, 1),
        gender=None,
        phone=None,
        email=None,
        address=None,
        status=StudentStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )


def test_create_data_cannot_be_used_in_edit_mode():
    app()
    dialog = StudentFormDialog(make_student())

    try:
        dialog.create_data()
    except RuntimeError:
        pass
    else:
        raise AssertionError("Phải chặn create_data trong EDIT mode.")


def test_update_data_cannot_be_used_in_create_mode():
    app()
    dialog = StudentFormDialog()

    try:
        dialog.update_data()
    except RuntimeError:
        pass
    else:
        raise AssertionError("Phải chặn update_data trong CREATE mode.")
