from __future__ import annotations

import inspect
import os
from datetime import date, datetime
from decimal import Decimal

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import QApplication, QFrame, QSplitter

from models.dto import (
    EnrollmentListItem,
    InterventionHistoryItem,
    ScoreListItem,
    Student,
    StudentProfileData,
)
from models.dto.student_list import StudentListItem
from models.enums import (
    EnrollmentStatus,
    InterventionStatus,
    StudentStatus,
)
from ui import theme
from ui.dialogs.enrollment_dialog import EnrollmentDialog
from ui.dialogs.student_form_dialog import StudentFormDialog
from ui.dialogs.student_profile_dialog import StudentProfileDialog
from ui.pages.students_page import StudentsPage


def app() -> QApplication:
    return QApplication.instance() or QApplication([])


def student_list_item() -> StudentListItem:
    return StudentListItem(
        "student-1",
        "HS001",
        "Nguyễn Văn An",
        date(2012, 1, 2),
        "Nam",
        "6A1",
        6,
        StudentStatus.ACTIVE,
        "2026-2027",
    )


class ProfileService:
    def get_profile(self, student_id: str) -> StudentProfileData:
        assert student_id == "student-1"
        now = datetime(2026, 1, 1)
        return StudentProfileData(
            student=Student(
                "student-1",
                "HS001",
                "Nguyễn Văn An",
                date(2012, 1, 2),
                "Nam",
                "0900000000",
                "an@example.com",
                "Hà Nội",
                StudentStatus.ACTIVE,
                now,
                now,
            ),
            enrollment_history=(
                EnrollmentListItem(
                    1,
                    "student-1",
                    "HS001",
                    "Nguyễn Văn An",
                    10,
                    "6A1",
                    6,
                    1,
                    "2026-2027",
                    EnrollmentStatus.ACTIVE,
                ),
            ),
            score_history=(
                ScoreListItem(
                    1,
                    1,
                    "student-1",
                    "HS001",
                    "Nguyễn Văn An",
                    "6A1",
                    "Toán",
                    "Giữa kỳ",
                    Decimal("8.50"),
                ),
            ),
            intervention_history=(
                InterventionHistoryItem(
                    1,
                    1,
                    "student-1",
                    "6A1",
                    "Toán",
                    Decimal("3.00"),
                    date(2026, 10, 1),
                    InterventionStatus.IN_PROGRESS,
                    "Phụ đạo nhóm",
                ),
            ),
        )


def test_students_theme_is_centralized_and_has_accessible_status_palette():
    stylesheet = theme.student_page_stylesheet()

    assert "QWidget#studentsPage" in stylesheet
    assert "QFrame#studentsToolbarFrame" in stylesheet
    assert "QWidget#studentsPage QTableWidget" in stylesheet
    foreground, background = theme.status_badge_colors(StudentStatus.ACTIVE)
    assert foreground == theme.SUCCESS
    assert background == theme.SUCCESS_SUBTLE


def test_students_page_uses_toolbar_split_content_cards_and_compact_table():
    app()
    page = StudentsPage()

    assert isinstance(page.toolbar_frame, QFrame)
    assert isinstance(page.content_splitter, QSplitter)
    assert page.content_splitter.orientation() == Qt.Orientation.Horizontal
    assert page.content_splitter.count() == 2
    assert page.table_card.objectName() == "studentsTableCard"
    assert page.details_card.objectName() == "studentsDetailsCard"
    assert page.table.showGrid() is False
    assert page.table.verticalHeader().defaultSectionSize() == 40
    assert page.table.horizontalHeader().minimumHeight() == 42


def test_students_page_switches_between_empty_state_and_real_rows():
    app()
    page = StudentsPage()

    assert page.table_stack.currentWidget() is page.empty_widget
    page.set_students((student_list_item(),))

    assert page.table_stack.currentWidget() is page.table
    assert page.table.item(0, 1).text() == "Nguyễn Văn An"
    assert page.table.item(0, 5).foreground().color().name().upper() == theme.SUCCESS
    assert page.count_label.text() == "1 học sinh"


def test_student_filters_are_labeled_searchable_and_clearable():
    app()
    page = StudentsPage()
    filters = page.filter_widget

    assert filters.search_input.isClearButtonEnabled()
    assert filters.search_input.minimumWidth() >= 260
    assert "mã học sinh" in filters.search_input.placeholderText().lower()
    assert all(
        combo is not None
        for combo in (
            filters.school_year_combo,
            filters.grade_combo,
            filters.class_combo,
            filters.status_combo,
        )
    )


def test_students_actions_keep_existing_scope_and_visual_hierarchy():
    app()
    page = StudentsPage()

    assert page.add_button.property("variant") == "primary"
    assert page.export_button.property("variant") == "secondary"
    assert page.refresh_button.property("variant") == "secondary"
    assert not hasattr(page, "delete_button")
    assert page.edit_button.isEnabled() is False
    assert page.profile_button.isEnabled() is False


def test_student_form_dialog_uses_shared_card_without_changing_form_contract():
    app()
    dialog = StudentFormDialog()

    assert dialog.objectName() == "studentFormDialog"
    assert dialog.form_card.property("dialogCard") is True
    assert dialog.title_label.property("dialogTitle") is True
    assert dialog.save_button.property("variant") == "primary"
    dialog.student_code_input.setText(" HS100 ")
    dialog.full_name_input.setText(" Nguyễn Văn An ")
    dialog.date_of_birth_input.setDate(QDate(2012, 1, 2))
    assert dialog.create_data().student_code == "HS100"


def test_enrollment_dialog_uses_shared_card_and_keeps_validation_contract():
    app()
    dialog = EnrollmentDialog()

    assert dialog.objectName() == "enrollmentDialog"
    assert dialog.form_card.property("dialogCard") is True
    assert dialog.save_button.property("variant") == "primary"
    assert dialog.validation_error() == "Vui lòng chọn năm học."


def test_student_profile_has_identity_header_four_tabs_and_saved_history():
    app()
    dialog = StudentProfileDialog("student-1", ProfileService())
    dialog.load_profile()

    assert dialog.profile_header.property("dialogCard") is True
    assert dialog.profile_name_label.text() == "Nguyễn Văn An"
    assert dialog.profile_context_label.text() == "Mã học sinh: HS001"
    assert dialog.avatar_label.text() == "VA"
    assert dialog.tabs.count() == 4
    assert [dialog.tabs.tabText(index) for index in range(4)] == [
        "Thông tin cơ bản",
        "Lịch sử lớp học",
        "Lịch sử điểm",
        "Lịch sử bổ trợ",
    ]
    assert dialog.score_table.item(0, 2).text() == "Giữa kỳ"
    status_cell = dialog.intervention_table.item(0, 4)
    assert status_cell.text() == "Đang bổ trợ"
    assert status_cell.foreground().color().name().upper() == theme.PRIMARY


def test_students_ui_layers_do_not_contain_sql_or_repository_access():
    sources = "\n".join(
        inspect.getsource(component)
        for component in (
            StudentsPage,
            StudentFormDialog,
            EnrollmentDialog,
            StudentProfileDialog,
        )
    ).upper()

    assert "SELECT " not in sources
    assert "INSERT " not in sources
    assert "UPDATE " not in sources
    assert "REPOSITORY" not in sources
