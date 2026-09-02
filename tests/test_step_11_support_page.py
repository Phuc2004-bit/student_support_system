from datetime import date
from decimal import Decimal
import inspect
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QComboBox

from models.dto.report_dto import SupportReportRow
from models.enums import InterventionStatus
from ui.pages.support_page import SupportPage


def app():
    return QApplication.instance() or QApplication([])


class AcademicStub:
    def __init__(self):
        self.year_calls = 0
        self.grade_calls = 0
        self.class_calls = []
        self.subject_calls = 0

    def list_school_years(self):
        self.year_calls += 1
        return [
            (1, "2025-2026", None, None, False),
            (2, "2026-2027", None, None, True),
        ]

    def list_grades(self):
        self.grade_calls += 1
        return [(6, 6, "Khối 6"), (7, 7, "Khối 7")]

    def list_classes_by_school_year(self, school_year_id):
        self.class_calls.append(school_year_id)
        return {
            1: [(51, "6A0", 6, None, True)],
            2: [
                (61, "6A1", 6, None, True),
                (62, "6A2", 6, None, True),
                (63, "6A3", 6, None, False),
                (71, "7A1", 7, None, True),
            ],
        }.get(school_year_id, [])

    def list_active_subjects(self):
        self.subject_calls += 1
        return [(11, "M1", "Môn 1"), (12, "M2", "Môn 2")]


class SupportReadStub:
    def __init__(self, rows=()):
        self.rows = list(rows)
        self.calls = []
        self.fail = False

    def get_support_cases(self, **filters):
        self.calls.append(filters)
        if self.fail:
            raise RuntimeError("raw database detail")
        return list(self.rows)


def support_row(status="DETECTED", responsible_user_name="Teacher A"):
    return SupportReportRow(
        intervention_id=101,
        student_code="HS001",
        full_name="Student A",
        grade_number=6,
        class_name="6A1",
        subject_code="M1",
        subject_name="Môn 1",
        detected_date=date(2026, 10, 10),
        start_date=None,
        status=status,
        trigger_score=Decimal("2.80"),
        student_id="student-101",
        enrollment_id=201,
        grade_id=6,
        class_id=61,
        subject_id=11,
        responsible_user_id=501,
        responsible_user_name=responsible_user_name,
    )


def select_data(combo, value):
    index = combo.findData(value)
    assert index >= 0
    combo.setCurrentIndex(index)


def test_support_page_builds_read_only_shell_with_five_filters():
    app()
    page = SupportPage()

    controls = (
        page.school_year_combo,
        page.grade_combo,
        page.class_combo,
        page.subject_combo,
        page.status_combo,
    )
    assert all(isinstance(control, QComboBox) for control in controls)
    assert page.objectName() == "supportPage"
    assert page.table.columnCount() == 10
    assert page.table.editTriggers() == (
        page.table.EditTrigger.NoEditTriggers
    )
    assert page.findChildren(type(page.refresh_button)) == [
        page.refresh_button
    ]


def test_initialize_loads_current_year_grades_classes_subjects_statuses():
    app()
    academic = AcademicStub()
    reader = SupportReadStub()
    page = SupportPage(academic, reader)

    assert page.initialize_support() is True
    assert academic.year_calls == 1
    assert academic.grade_calls == 1
    assert academic.class_calls == [2]
    assert academic.subject_calls == 1
    assert page.school_year_combo.currentData() == 2
    assert page.grade_combo.count() == 3
    assert page.class_combo.count() == 4
    assert page.subject_combo.count() == 3
    assert page.status_combo.count() == 7
    assert [
        page.status_combo.itemData(index)
        for index in range(1, page.status_combo.count())
    ] == list(InterventionStatus)
    assert len(reader.calls) == 1


def test_grade_filters_classes_and_all_filters_reach_read_contract():
    app()
    reader = SupportReadStub()
    page = SupportPage(AcademicStub(), reader)
    page.initialize_support()

    select_data(page.grade_combo, 6)
    assert page.class_combo.count() == 3
    assert page.class_combo.findData(61) >= 0
    assert page.class_combo.findData(62) >= 0
    assert page.class_combo.findData(63) == -1
    assert page.class_combo.findData(71) == -1

    select_data(page.class_combo, 61)
    select_data(page.subject_combo, 11)
    select_data(page.status_combo, InterventionStatus.DETECTED)

    assert reader.calls[-1] == {
        "school_year_id": 2,
        "grade_id": 6,
        "class_id": 61,
        "subject_id": 11,
        "status": InterventionStatus.DETECTED,
    }


def test_year_change_resets_grade_and_class_and_loads_matching_classes():
    app()
    academic = AcademicStub()
    page = SupportPage(academic, SupportReadStub())
    page.initialize_support()
    select_data(page.grade_combo, 7)
    select_data(page.class_combo, 71)

    select_data(page.school_year_combo, 1)

    assert academic.class_calls[-1] == 1
    assert page.grade_combo.currentData() is None
    assert page.class_combo.currentData() is None
    assert page.class_combo.count() == 2
    assert page.class_combo.itemData(1) == 51


def test_render_support_row_keeps_id_and_formats_values():
    app()
    row = support_row(status="COMPLETED")
    page = SupportPage()

    page.set_support_cases([row])

    assert page.table.rowCount() == 1
    assert page.intervention_id_at_row(0) == 101
    assert page.table.item(0, 0).data(Qt.ItemDataRole.UserRole) == 101
    assert page.table.item(0, 1).text() == "HS001"
    assert page.table.item(0, 2).text() == "Student A"
    assert page.table.item(0, 6).text() == "2.80"
    assert page.table.item(0, 7).text() == "10/10/2026"
    assert page.table.item(0, 8).text() == "Đã đạt ngưỡng"
    assert page.table.item(0, 9).text() == "Teacher A"
    assert page.count_label.text() == "1 hồ sơ bổ trợ"


def test_missing_responsible_user_uses_safe_placeholder():
    app()
    page = SupportPage()

    page.set_support_cases([support_row(responsible_user_name=None)])

    assert page.table.item(0, 9).text() == "—"


def test_empty_result_is_visible_and_does_not_create_dummy_row():
    app()
    page = SupportPage(AcademicStub(), SupportReadStub())

    assert page.initialize_support() is True
    assert page.load_state == page.STATE_EMPTY
    assert page.table.rowCount() == 0
    assert page.table.isHidden()
    assert page.empty_label.text() == page.EMPTY_MESSAGE


def test_read_failure_is_normalized_and_page_can_retry():
    app()
    reader = SupportReadStub([support_row()])
    reader.fail = True
    page = SupportPage(AcademicStub(), reader)

    assert page.initialize_support() is True
    assert page.load_state == page.STATE_ERROR
    assert "raw database detail" not in page.state_label.text()
    assert page.refresh_button.isEnabled()

    reader.fail = False
    assert page.refresh_support_cases() is True
    assert page.load_state == page.STATE_SUCCESS
    assert page.table.rowCount() == 1


def test_refresh_uses_one_list_operation_and_exposes_loading_state():
    app()

    class LoadingAwareReader(SupportReadStub):
        def get_support_cases(self, **filters):
            assert page.load_state == page.STATE_LOADING
            assert page.refresh_button.isEnabled() is False
            return super().get_support_cases(**filters)

    reader = LoadingAwareReader([support_row()])
    page = SupportPage(AcademicStub(), reader)
    page.initialize_support()
    reader.calls.clear()

    assert page.refresh_support_cases() is True
    assert len(reader.calls) == 1


def test_missing_or_empty_dependencies_do_not_crash():
    app()

    class EmptyAcademic:
        def list_school_years(self):
            return []

        def list_grades(self):
            return []

        def list_classes_by_school_year(self, _school_year_id):
            return []

        def list_active_subjects(self):
            return []

    page_without_service = SupportPage()
    empty_page = SupportPage(EmptyAcademic(), SupportReadStub())

    assert page_without_service.initialize_support() is False
    assert empty_page.initialize_support() is True
    assert empty_page.school_year_combo.currentData() is None
    assert empty_page.table.rowCount() == 0


def test_support_ui_has_no_sql_repository_or_transition_dependencies():
    page_source = inspect.getsource(SupportPage).upper()
    module_source = inspect.getsource(
        inspect.getmodule(SupportPage)
    ).upper()

    assert "SELECT " not in module_source
    assert "INSERT " not in module_source
    assert "UPDATE " not in module_source
    assert "DELETE " not in module_source
    assert "REPOSITORY" not in module_source
    assert "SUPPORTSERVICE" not in module_source
    for transition_method in (
        "PLAN_INTERVENTION",
        "START_INTERVENTION",
        "MARK_WAITING_REVIEW",
        "CONTINUE_INTERVENTION",
        "REVIEW_INTERVENTION",
    ):
        assert transition_method not in page_source
