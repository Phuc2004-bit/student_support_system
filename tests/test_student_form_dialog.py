import os
from datetime import date, datetime

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QDate
from PySide6.QtWidgets import QApplication

from models.dto import Student
from models.enums import StudentStatus
from ui.dialogs.student_form_dialog import StudentFormDialog


def app():
    return QApplication.instance() or QApplication([])


def student():
    now = datetime.now()
    return Student(
        student_id="id-1",
        student_code="HS001",
        full_name="Nguyễn Văn A",
        date_of_birth=date(2012, 5, 10),
        gender="Nam",
        phone="0912345678",
        email="a@example.com",
        address="Hà Nội",
        status=StudentStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )


def test_create_mode_has_expected_fields():
    app()
    dialog = StudentFormDialog()

    assert dialog.mode == dialog.MODE_CREATE
    assert dialog.student_code_input.isEnabled()
    assert dialog.save_button.text() == "Thêm học sinh"


def test_create_data_builds_student_create_dto():
    app()
    dialog = StudentFormDialog()

    dialog.student_code_input.setText(" HS100 ")
    dialog.full_name_input.setText(" Trần Thị Lan ")
    dialog.date_of_birth_input.setDate(QDate(2011, 3, 4))
    dialog.gender_combo.setCurrentIndex(
        dialog.gender_combo.findData("Nữ")
    )
    dialog.phone_input.setText("0912345678")
    dialog.email_input.setText("lan@example.com")
    dialog.address_input.setPlainText("Đà Nẵng")

    data = dialog.create_data()

    assert data.student_code == "HS100"
    assert data.full_name == "Trần Thị Lan"
    assert data.date_of_birth == date(2011, 3, 4)
    assert data.gender == "Nữ"
    assert data.phone == "0912345678"
    assert data.email == "lan@example.com"
    assert data.address == "Đà Nẵng"


def test_edit_mode_prefills_student_and_locks_code():
    app()
    dialog = StudentFormDialog(student())

    assert dialog.mode == dialog.MODE_EDIT
    assert dialog.student_code_input.text() == "HS001"
    assert dialog.student_code_input.isEnabled() is False
    assert dialog.full_name_input.text() == "Nguyễn Văn A"
    assert dialog.save_button.text() == "Cập nhật"


def test_update_data_does_not_contain_student_code():
    app()
    dialog = StudentFormDialog(student())

    dialog.full_name_input.setText("Nguyễn Văn B")
    data = dialog.update_data()

    assert data.full_name == "Nguyễn Văn B"
    assert not hasattr(data, "student_code")


def test_required_name_validation():
    app()
    dialog = StudentFormDialog()
    dialog.student_code_input.setText("HS001")
    dialog.full_name_input.setText("")

    assert (
        dialog.validation_error()
        == "Họ và tên học sinh không được để trống."
    )


def test_create_requires_student_code():
    app()
    dialog = StudentFormDialog()
    dialog.full_name_input.setText("Nguyễn Văn A")

    assert (
        dialog.validation_error()
        == "Mã học sinh không được để trống."
    )


def test_invalid_email_is_rejected():
    app()
    dialog = StudentFormDialog()
    dialog.student_code_input.setText("HS001")
    dialog.full_name_input.setText("Nguyễn Văn A")
    dialog.email_input.setText("abc")

    assert dialog.validation_error() == "Email không hợp lệ."


def test_non_digit_phone_is_rejected():
    app()
    dialog = StudentFormDialog()
    dialog.student_code_input.setText("HS001")
    dialog.full_name_input.setText("Nguyễn Văn A")
    dialog.phone_input.setText("09A123")

    assert (
        dialog.validation_error()
        == "Số điện thoại chỉ được chứa chữ số."
    )
