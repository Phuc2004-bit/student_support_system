import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from models.dto.enrollment import EnrollmentListItem
from models.enums import EnrollmentStatus
from ui.widgets.current_enrollment_widget import (
    CurrentEnrollmentWidget,
)


def app():
    return QApplication.instance() or QApplication([])


def item():
    return EnrollmentListItem(
        enrollment_id=1,
        student_id="student-1",
        student_code="HS001",
        full_name="Nguyễn Văn A",
        class_id=10,
        class_name="6A1",
        grade_number=6,
        school_year_id=2,
        school_year_name="2026-2027",
        status=EnrollmentStatus.ACTIVE,
    )


def test_empty_state_shows_assign_action():
    app()
    widget = CurrentEnrollmentWidget()

    assert widget.enrollment is None
    assert widget.class_label.text() == "Chưa xếp lớp"
    assert widget.assign_button.isHidden() is False
    assert widget.transfer_button.isHidden() is True


def test_active_enrollment_is_rendered():
    app()
    widget = CurrentEnrollmentWidget()
    widget.set_enrollment(item())

    assert widget.class_label.text() == "6A1"
    assert widget.year_label.text() == "Năm học: 2026-2027"
    assert widget.grade_label.text() == "Khối: 6"
    assert widget.assign_button.isHidden() is True
    assert widget.transfer_button.isHidden() is False


def test_assign_signal():
    app()
    widget = CurrentEnrollmentWidget()
    calls = []
    widget.assign_requested.connect(
        lambda: calls.append(True)
    )

    widget.assign_button.click()

    assert calls == [True]


def test_transfer_signal():
    app()
    widget = CurrentEnrollmentWidget()
    widget.set_enrollment(item())

    calls = []
    widget.transfer_requested.connect(
        lambda: calls.append(True)
    )

    widget.transfer_button.click()

    assert calls == [True]
