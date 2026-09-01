import os
from datetime import date

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from models.dto.student_filter import StudentFilter
from models.dto.student_list import StudentListItem
from models.enums import StudentStatus
from ui.pages.students_page import StudentsPage


def app():
    return QApplication.instance() or QApplication([])


def row(
    student_id="id-1",
    code="HS001",
    name="Nguyễn Văn A",
    class_name="6A1",
    grade=6,
):
    return StudentListItem(
        student_id=student_id,
        student_code=code,
        full_name=name,
        date_of_birth=date(2012, 1, 2),
        gender="Nam",
        current_class_name=class_name,
        current_grade_number=grade,
        status=StudentStatus.ACTIVE,
    )


class AcademicStub:
    def list_school_years(self):
        return [
            (
                2,
                "2026-2027",
                None,
                None,
                True,
            )
        ]

    def list_grades(self):
        return [
            (6, 6, "Khối 6"),
            (7, 7, "Khối 7"),
        ]

    def list_classes_by_school_year(
        self,
        school_year_id,
    ):
        assert school_year_id == 2
        return [
            (61, "6A1", 6, True),
            (71, "7A1", 7, True),
        ]


class StudentListServiceStub:
    def __init__(self):
        self.filters = []

    def list_students(
        self,
        filters=None,
    ):
        self.filters.append(filters)

        if filters is None:
            return [row()]

        if filters.grade_id == 7:
            return [
                row(
                    student_id="id-7",
                    code="HS007",
                    name="Trần Thị B",
                    class_name="7A1",
                    grade=7,
                )
            ]

        if filters.search_text.strip() == "Lan":
            return [
                row(
                    student_id="id-lan",
                    code="HS009",
                    name="Nguyễn Thị Lan",
                )
            ]

        return [row()]


def test_initialize_students_loads_options_and_data():
    app()
    service = StudentListServiceStub()
    page = StudentsPage(
        student_service=service,
        academic_service=AcademicStub(),
    )

    assert page.initialize_students() is True

    assert len(service.filters) == 1
    assert service.filters[0].school_year_id == 2
    assert page.table.rowCount() == 1
    assert page.count_label.text() == "1 học sinh"


def test_grade_filter_refreshes_table():
    app()
    service = StudentListServiceStub()
    page = StudentsPage(
        student_service=service,
        academic_service=AcademicStub(),
    )
    page.initialize_students()

    page.filter_widget.grade_combo.setCurrentIndex(2)

    assert service.filters[-1].grade_id == 7
    assert page.table.rowCount() == 1
    assert page.table.item(0, 0).text() == "HS007"
    assert page.table.item(0, 4).text() == "7A1"


def test_search_filter_reaches_service_and_updates_table():
    app()
    service = StudentListServiceStub()
    page = StudentsPage(
        student_service=service,
        academic_service=AcademicStub(),
    )
    page.initialize_students()

    page.filter_widget.search_input.setText("Lan")
    page.filter_widget._timer.stop()
    page.filter_widget._emit()

    assert service.filters[-1].search_text == "Lan"
    assert page.table.item(0, 1).text() == "Nguyễn Thị Lan"


def test_manual_refresh_uses_current_filter():
    app()
    service = StudentListServiceStub()
    page = StudentsPage(
        student_service=service,
        academic_service=AcademicStub(),
    )
    page.initialize_students()

    page.filter_widget.grade_combo.setCurrentIndex(1)
    before = len(service.filters)

    assert page.refresh_students() is True

    assert len(service.filters) == before + 1
    assert service.filters[-1].grade_id == 6


def test_last_filter_tracks_latest_filter():
    app()
    service = StudentListServiceStub()
    page = StudentsPage(
        student_service=service,
        academic_service=AcademicStub(),
    )
    page.initialize_students()

    page.filter_widget.status_combo.setCurrentIndex(1)

    assert page.last_filter.status == StudentStatus.ACTIVE


def test_page_remains_backward_compatible_without_academic_service():
    app()
    service = StudentListServiceStub()
    page = StudentsPage(student_service=service)

    assert page.initialize_students() is True
    assert len(service.filters) == 1
    assert service.filters[0] == StudentFilter()
