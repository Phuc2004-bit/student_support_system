from datetime import date
import inspect
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialog, QTabWidget

from models.dto import Grade, SchoolClass, SchoolYear
from ui.dialogs.catalog_dialogs import ClassDialog, GradeDialog, SchoolYearDialog
from ui.main_window import MainWindow
from ui.pages.catalog_page import CatalogPage


def app():
    return QApplication.instance() or QApplication([])


class CatalogStub:
    def __init__(self):
        self.years = [
            SchoolYear(1, "2025-2026", date(2025, 9, 1), date(2026, 5, 31), False),
            SchoolYear(2, "2026-2027", date(2026, 9, 1), date(2027, 5, 31), True),
        ]
        self.grades = [Grade(6, 6, "Khối 6"), Grade(7, 7, "Khối 7")]
        self.all_classes = [
            SchoolClass(61, "6A1", 6, 6, 2, "2026-2027", "GV A", "ACTIVE"),
            SchoolClass(62, "6A2", 6, 6, 2, "2026-2027", None, "INACTIVE"),
            SchoolClass(71, "7A1", 7, 7, 2, "2026-2027", "GV B", "ACTIVE"),
        ]
        self.class_calls = []
        self.write_calls = []
        self.fail = False

    def list_catalog_school_years(self):
        if self.fail:
            raise RuntimeError("raw pyodbc failure")
        return list(self.years)

    def list_catalog_grades(self):
        return list(self.grades)

    def list_catalog_classes(self, school_year_id, grade_id=None):
        self.class_calls.append((school_year_id, grade_id))
        return [
            item for item in self.all_classes
            if item.school_year_id == school_year_id
            and (grade_id is None or item.grade_id == grade_id)
        ]

    def create_school_year(self, *values):
        self.write_calls.append(("create_year", *values))

    def update_school_year(self, *values):
        self.write_calls.append(("update_year", *values))

    def create_grade(self, *values):
        self.write_calls.append(("create_grade", *values))

    def update_grade_name(self, *values):
        self.write_calls.append(("update_grade", *values))

    def create_class(self, *values):
        self.write_calls.append(("create_class", *values))

    def update_class(self, *values):
        self.write_calls.append(("update_class", *values))

    def set_class_active(self, *values):
        self.write_calls.append(("set_class_active", *values))


class AcceptedDialog:
    DialogCode = QDialog.DialogCode

    def __init__(self, values):
        self._values = values

    def exec(self):
        return self.DialogCode.Accepted

    def values(self):
        return self._values


class RejectedDialog(AcceptedDialog):
    def exec(self):
        return self.DialogCode.Rejected


def test_catalog_page_builds_three_required_tabs():
    app()
    page = CatalogPage()

    assert page.title_label.text() == "Danh mục"
    assert isinstance(page.tabs, QTabWidget)
    assert page.tabs.count() == 3
    assert [page.tabs.tabText(i) for i in range(3)] == ["Năm học", "Khối", "Lớp"]


def test_initialize_loads_school_years_grades_and_current_year_classes():
    app()
    service = CatalogStub()
    page = CatalogPage(service)

    assert page.initialize_catalogs() is True

    assert page.school_year_table.rowCount() == 2
    assert page.grade_table.rowCount() == 2
    assert page.class_year_combo.currentData() == 2
    assert service.class_calls[-1] == (2, None)
    assert page.class_table.rowCount() == 3


def test_catalog_tables_preserve_database_ids_in_user_role():
    app()
    page = CatalogPage(CatalogStub())
    page.initialize_catalogs()

    assert page.school_year_table.item(0, 0).data(Qt.ItemDataRole.UserRole) == 1
    assert page.grade_table.item(0, 0).data(Qt.ItemDataRole.UserRole) == 6
    assert page.class_table.item(0, 0).data(Qt.ItemDataRole.UserRole) == 61


def test_class_filter_uses_selected_year_id():
    app()
    service = CatalogStub()
    page = CatalogPage(service)
    page.initialize_catalogs()

    page.class_year_combo.setCurrentIndex(page.class_year_combo.findData(1))

    assert service.class_calls[-1] == (1, None)
    assert page.class_table.rowCount() == 0


def test_class_filter_uses_grade_id_and_excludes_other_grades():
    app()
    service = CatalogStub()
    page = CatalogPage(service)
    page.initialize_catalogs()

    page.class_grade_combo.setCurrentIndex(page.class_grade_combo.findData(7))

    assert service.class_calls[-1] == (2, 7)
    assert page.class_table.rowCount() == 1
    assert page.class_table.item(0, 0).text() == "7A1"


def test_school_year_table_renders_dates_and_current_state():
    app()
    page = CatalogPage(CatalogStub())
    page.initialize_catalogs()

    assert page.school_year_table.item(1, 0).text() == "2026-2027"
    assert page.school_year_table.item(1, 1).text() == "01/09/2026"
    assert page.school_year_table.item(1, 3).text() == "Có"


def test_grade_table_uses_service_values_not_hard_coded_options():
    app()
    service = CatalogStub()
    service.grades = [Grade(99, 11, "Khối chuyên")]
    page = CatalogPage(service)

    page.initialize_catalogs()

    assert page.grade_table.item(0, 0).text() == "11"
    assert page.grade_table.item(0, 1).text() == "Khối chuyên"
    assert page.class_grade_combo.itemData(1) == 99


def test_class_table_shows_active_and_inactive_without_deleting_history():
    app()
    page = CatalogPage(CatalogStub())
    page.initialize_catalogs()

    assert page.class_table.item(0, 4).text() == "Đang sử dụng"
    assert page.class_table.item(1, 4).text() == "Ngừng sử dụng"
    assert page.class_table.rowCount() == 3


def test_create_school_year_passes_dialog_values_to_service():
    app()
    service = CatalogStub()
    values = ("2027-2028", date(2027, 9, 1), date(2028, 5, 31), False)
    page = CatalogPage(
        service,
        school_year_dialog_factory=lambda _item, _parent: AcceptedDialog(values),
    )
    page.initialize_catalogs()

    assert page.create_school_year() is True
    assert service.write_calls[-1] == ("create_year", *values)


def test_edit_school_year_uses_selected_identity():
    app()
    service = CatalogStub()
    values = ("2025-2026 sửa", date(2025, 8, 1), date(2026, 6, 1), True)
    page = CatalogPage(
        service,
        school_year_dialog_factory=lambda _item, _parent: AcceptedDialog(values),
    )
    page.initialize_catalogs()
    page.school_year_table.setCurrentCell(0, 0)

    assert page.edit_school_year() is True
    assert service.write_calls[-1] == ("update_year", 1, *values)


def test_create_and_edit_grade_keep_database_identity():
    app()
    service = CatalogStub()
    page = CatalogPage(
        service,
        grade_dialog_factory=lambda item, _parent: AcceptedDialog(
            (8, "Khối 8") if item is None else (item.grade_number, "Tên mới")
        ),
    )
    page.initialize_catalogs()

    assert page.create_grade() is True
    page.grade_table.setCurrentCell(0, 0)
    assert page.edit_grade() is True

    assert ("create_grade", 8, "Khối 8") in service.write_calls
    assert service.write_calls[-1] == ("update_grade", 6, "Tên mới")


def test_create_class_passes_year_and_grade_ids_not_display_text():
    app()
    service = CatalogStub()
    values = ("6A3", 6, 2, "GV C", "ACTIVE")
    page = CatalogPage(
        service,
        class_dialog_factory=lambda *_args: AcceptedDialog(values),
    )
    page.initialize_catalogs()

    assert page.create_class() is True
    assert service.write_calls[-1] == ("create_class", *values)


def test_edit_class_preserves_selected_class_id_and_new_fk_ids():
    app()
    service = CatalogStub()
    values = ("6A1 mới", 6, 2, "GV mới", "INACTIVE")
    page = CatalogPage(
        service,
        class_dialog_factory=lambda *_args: AcceptedDialog(values),
    )
    page.initialize_catalogs()
    page.class_table.setCurrentCell(0, 0)

    assert page.edit_class() is True
    assert service.write_calls[-1] == ("update_class", 61, *values)


def test_toggle_class_uses_selected_id_and_inverse_active_state():
    app()
    service = CatalogStub()
    page = CatalogPage(service)
    page.initialize_catalogs()
    page.class_table.setCurrentCell(0, 0)

    assert page.toggle_class_active() is True
    assert service.write_calls[-1] == ("set_class_active", 61, False)


def test_cancelled_dialog_does_not_write():
    app()
    service = CatalogStub()
    page = CatalogPage(
        service,
        school_year_dialog_factory=lambda *_args: RejectedDialog(()),
    )
    page.initialize_catalogs()

    assert page.create_school_year() is False
    assert service.write_calls == []


def test_missing_selection_does_not_write_or_crash():
    app()
    service = CatalogStub()
    page = CatalogPage(service)
    page.initialize_catalogs()

    assert page.edit_school_year() is False
    assert page.edit_grade() is False
    assert page.edit_class() is False
    assert page.toggle_class_active() is False
    assert service.write_calls == []


def test_service_error_is_normalized_in_page_state():
    app()
    service = CatalogStub()
    service.fail = True
    page = CatalogPage(service)

    assert page.initialize_catalogs() is False
    assert "pyodbc" not in page.state_label.text().lower()
    assert "raw" not in page.state_label.text().lower()


def test_catalog_dialogs_store_fk_ids_and_lock_grade_number_on_edit():
    app()
    years = [SchoolYear(2, "2026-2027", None, None, True)]
    grades = [Grade(6, 6, "Khối 6")]
    school_class = SchoolClass(61, "6A1", 6, 6, 2, "2026-2027", None, "ACTIVE")

    class_dialog = ClassDialog(years, grades, school_class)
    grade_dialog = GradeDialog(grades[0])
    year_dialog = SchoolYearDialog(years[0])

    assert class_dialog.school_year_combo.currentData() == 2
    assert class_dialog.grade_combo.currentData() == 6
    assert class_dialog.values()[1:3] == (6, 2)
    assert not grade_dialog.grade_number_input.isEnabled()
    assert year_dialog.values()[0] == "2026-2027"


def test_catalog_ui_has_no_sql_repository_or_direct_transaction_logic():
    source = inspect.getsource(inspect.getmodule(CatalogPage)).upper()
    for forbidden in (
        "SELECT ",
        "INSERT ",
        "UPDATE ",
        "DELETE ",
        "REPOSITORY",
        "TRANSACTION",
        ".COMMIT(",
    ):
        assert forbidden not in source


def test_catalog_page_is_not_integrated_into_main_window_in_step_12_5():
    source = inspect.getsource(MainWindow)

    assert "CatalogPage" not in source
