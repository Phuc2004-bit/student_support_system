import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from models.dto.enrollment import EnrollmentListItem
from models.enums import EnrollmentStatus
from ui.widgets.enrollment_history_widget import (
    EnrollmentHistoryWidget,
)


def app():
    return QApplication.instance() or QApplication([])


def item(
    enrollment_id: int,
    class_name: str,
    status: EnrollmentStatus,
) -> EnrollmentListItem:
    return EnrollmentListItem(
        enrollment_id=enrollment_id,
        student_id="student-1",
        student_code="HS001",
        full_name="Nguyễn Văn A",
        class_id=enrollment_id,
        class_name=class_name,
        grade_number=6,
        school_year_id=2,
        school_year_name="2026-2027",
        status=status,
    )


def test_history_renders_all_enrollments_with_statuses():
    app()
    widget = EnrollmentHistoryWidget()
    history = (
        item(1, "6A1", EnrollmentStatus.TRANSFERRED),
        item(2, "6A2", EnrollmentStatus.ACTIVE),
    )

    widget.set_history(history)

    assert widget.history == history
    assert widget.table.rowCount() == 2
    assert widget.table.item(0, 0).text() == "2026-2027"
    assert widget.table.item(0, 1).text() == "6"
    assert widget.table.item(0, 2).text() == "6A1"
    assert widget.table.item(0, 3).text() == "Đã chuyển lớp"
    assert widget.table.item(1, 3).text() == "Đang học"


def test_history_can_be_cleared_when_no_student_is_selected():
    app()
    widget = EnrollmentHistoryWidget()
    widget.set_history((item(1, "6A1", EnrollmentStatus.ACTIVE),))

    widget.set_history(())

    assert widget.history == ()
    assert widget.table.rowCount() == 0
