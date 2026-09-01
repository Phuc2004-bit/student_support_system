import os
from datetime import date, datetime
from decimal import Decimal

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from models.dto import (
    EnrollmentListItem,
    InterventionHistoryItem,
    ScoreListItem,
    Student,
    StudentProfileData,
)
from models.enums import EnrollmentStatus, InterventionStatus, StudentStatus
from ui.dialogs.student_profile_dialog import StudentProfileDialog


def app():
    return QApplication.instance() or QApplication([])


class ProfileService:
    def get_profile(self, student_id):
        assert student_id == "student-1"
        return StudentProfileData(
            student=Student(
                "student-1", "HS001", "Nguyễn Văn A", date(2012, 1, 2),
                "Nam", "0900000000", "a@example.com", "Hà Nội",
                StudentStatus.ACTIVE, datetime(2026, 1, 1), datetime(2026, 1, 1),
            ),
            enrollment_history=(EnrollmentListItem(
                1, "student-1", "HS001", "Nguyễn Văn A", 10, "6A1", 6,
                1, "2026-2027", EnrollmentStatus.ACTIVE,
            ),),
            score_history=(ScoreListItem(
                1, 1, "student-1", "HS001", "Nguyễn Văn A", "6A1",
                "Toán", "Giữa kỳ", Decimal("8.50"),
            ),),
            intervention_history=(InterventionHistoryItem(
                1, 1, "student-1", "6A1", "Toán", Decimal("3.00"),
                date(2026, 10, 1), InterventionStatus.COMPLETED,
                "Phụ đạo nhóm",
            ),),
        )


def test_profile_has_four_tabs_and_renders_saved_history():
    app()
    dialog = StudentProfileDialog("student-1", ProfileService())

    dialog.load_profile()

    assert dialog.tabs.count() == 4
    assert [dialog.tabs.tabText(index) for index in range(4)] == [
        "Thông tin cơ bản",
        "Lịch sử lớp học",
        "Lịch sử điểm",
        "Lịch sử bổ trợ",
    ]
    assert dialog.full_name_label.text() == "Nguyễn Văn A"
    assert dialog.enrollment_history_widget.table.rowCount() == 1
    assert dialog.score_table.item(0, 2).text() == "Giữa kỳ"
    assert dialog.intervention_table.item(0, 4).text() == "Đã hoàn thành"
