import os
from dataclasses import dataclass
from datetime import date

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QDate
from PySide6.QtWidgets import QApplication

from ui.dialogs.enrollment_dialog import EnrollmentDialog


def app():
    return QApplication.instance() or QApplication([])


@dataclass
class Year:
    school_year_id: int
    year_name: str
    is_current: bool


@dataclass
class ClassItem:
    class_id: int
    class_name: str
    is_active: bool = True


class Academic:
    def list_school_years(self):
        return [
            Year(1, "2025-2026", False),
            Year(2, "2026-2027", True),
        ]

    def list_classes_by_school_year(self, year_id):
        assert year_id == 2
        return [
            ClassItem(10, "6A1"),
            ClassItem(11, "6A2"),
        ]


def test_assign_dialog_loads_current_year_and_classes():
    app()
    dialog = EnrollmentDialog(
        academic_service=Academic()
    )
    dialog.load_options()

    assert dialog.school_year_combo.currentData() == 2
    assert dialog.class_combo.count() == 3


def test_selected_class_and_date():
    app()
    dialog = EnrollmentDialog(
        academic_service=Academic()
    )
    dialog.load_options()
    dialog.class_combo.setCurrentIndex(1)
    dialog.action_date_input.setDate(
        QDate(2026, 9, 7)
    )

    assert dialog.selected_class_id() == 10
    assert dialog.action_date() == date(2026, 9, 7)


def test_transfer_excludes_current_class():
    app()
    dialog = EnrollmentDialog(
        academic_service=Academic(),
        mode=EnrollmentDialog.MODE_TRANSFER,
        current_class_id=10,
    )
    dialog.load_options()

    ids = [
        dialog.class_combo.itemData(index)
        for index in range(
            dialog.class_combo.count()
        )
    ]

    assert 10 not in ids
    assert 11 in ids


def test_validation_requires_year():
    app()
    dialog = EnrollmentDialog()
    assert (
        dialog.validation_error()
        == "Vui lòng chọn năm học."
    )


def test_validation_requires_class():
    app()
    dialog = EnrollmentDialog(
        academic_service=Academic()
    )
    dialog.load_options()
    dialog.class_combo.setCurrentIndex(0)

    assert (
        dialog.validation_error()
        == "Vui lòng chọn lớp."
    )
