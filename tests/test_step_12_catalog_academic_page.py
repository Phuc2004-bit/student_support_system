from datetime import date, datetime
from decimal import Decimal
import inspect
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialog

from models.dto import Assessment, Grade, SchoolYear, Subject, SupportRule
from models.enums import AssessmentStatus
from ui.dialogs.catalog_dialogs import AssessmentDialog, SubjectDialog, SupportRuleDialog
from ui.pages.catalog_page import CatalogPage


NOW = datetime(2026, 1, 1)


def app():
    return QApplication.instance() or QApplication([])


class ServiceStub:
    def __init__(self):
        self.years = [
            SchoolYear(10, "2026-2027", date(2026, 9, 1), date(2027, 5, 31), True),
            SchoolYear(11, "2027-2028", date(2027, 9, 1), date(2028, 5, 31), False),
        ]
        self.grades = [Grade(6, 6, "Khối 6")]
        self.subjects = [
            Subject(1, "SCI", "Science", True),
            Subject(2, "OLD", "Historical", False),
        ]
        self.assessments = [
            Assessment(100, 1, 10, "Science test", 1, "QUIZ", date(2026, 10, 1), AssessmentStatus.ACTIVE, NOW),
            Assessment(101, 2, 10, "Old test", None, None, None, AssessmentStatus.CANCELLED, NOW),
            Assessment(102, 1, 11, "Next test", 2, "FINAL", None, AssessmentStatus.LOCKED, NOW),
        ]
        self.rules = [
            SupportRule(5, 1, 10, Decimal("4.25"), True, NOW, NOW),
            SupportRule(6, 2, 10, Decimal("3.00"), False, NOW, NOW),
        ]
        self.assessment_calls = []
        self.rule_calls = []
        self.writes = []

    def list_catalog_school_years(self): return list(self.years)
    def list_catalog_grades(self): return list(self.grades)
    def list_catalog_classes(self, school_year_id, grade_id=None): return []
    def list_catalog_subjects(self): return list(self.subjects)

    def list_assessments(self, school_year_id, subject_id=None, **_filters):
        self.assessment_calls.append((school_year_id, subject_id))
        return [x for x in self.assessments if x.school_year_id == school_year_id and (
            subject_id is None or x.subject_id == subject_id
        )]

    def list_catalog_support_rules(self, school_year_id, subject_id=None):
        self.rule_calls.append((school_year_id, subject_id))
        return [x for x in self.rules if x.school_year_id == school_year_id and (
            subject_id is None or x.subject_id == subject_id
        )]

    def create_subject(self, *args): self.writes.append(("create_subject", *args))
    def update_subject(self, *args): self.writes.append(("update_subject", *args))
    def set_subject_active(self, *args): self.writes.append(("set_subject_active", *args))
    def create_assessment(self, *args): self.writes.append(("create_assessment", *args))
    def update_assessment(self, *args): self.writes.append(("update_assessment", *args))
    def set_assessment_active(self, *args): self.writes.append(("set_assessment_active", *args))
    def create_support_rule(self, *args): self.writes.append(("create_rule", *args))
    def update_support_rule_threshold(self, *args): self.writes.append(("update_rule", *args))
    def set_support_rule_active(self, *args): self.writes.append(("set_rule_active", *args))


class AcceptedDialog:
    DialogCode = QDialog.DialogCode

    def __init__(self, values): self._values = values
    def exec(self): return self.DialogCode.Accepted
    def values(self): return self._values


def test_catalog_page_adds_three_academic_catalog_sections_without_main_window_wiring():
    app()
    page = CatalogPage()
    assert page.tabs.count() == 3
    assert page.advanced_tabs.count() == 3
    assert [page.advanced_tabs.tabText(i) for i in range(3)] == [
        "Môn học", "Bài đánh giá", "Ngưỡng bổ trợ"
    ]


def test_initialize_loads_subject_assessment_and_rule_history_from_service():
    app()
    page = CatalogPage(ServiceStub())
    assert page.initialize_catalogs() is True
    assert page.subject_table.rowCount() == 2
    assert page.assessment_table.rowCount() == 2
    assert page.rule_table.rowCount() == 2
    assert page.subject_table.item(1, 2).text() == "Ngừng sử dụng"
    assert page.assessment_table.item(1, 6).text() == "Ngừng sử dụng"
    assert page.rule_table.item(1, 2).text() == "3.00"


def test_assessment_filters_use_school_year_and_subject_ids():
    app()
    service = ServiceStub()
    page = CatalogPage(service)
    page.initialize_catalogs()
    page.assessment_subject_combo.setCurrentIndex(
        page.assessment_subject_combo.findData(1)
    )
    assert service.assessment_calls[-1] == (10, 1)
    assert page.assessment_table.rowCount() == 1
    page.assessment_year_combo.setCurrentIndex(
        page.assessment_year_combo.findData(11)
    )
    assert service.assessment_calls[-1] == (11, 1)
    assert page.assessment_table.item(0, 0).text() == "Next test"


def test_support_rule_filters_use_real_scope_without_invented_grade_id():
    app()
    service = ServiceStub()
    page = CatalogPage(service)
    page.initialize_catalogs()
    page.rule_subject_combo.setCurrentIndex(page.rule_subject_combo.findData(2))
    assert service.rule_calls[-1] == (10, 2)
    assert page.rule_table.rowCount() == 1
    assert not hasattr(page, "rule_grade_combo")


def test_subject_actions_preserve_identity_and_active_state():
    app()
    service = ServiceStub()
    page = CatalogPage(
        service,
        subject_dialog_factory=lambda item, _parent: AcceptedDialog(
            ("ART", "Art", True) if item is None else ("SCI2", "New Science", False)
        ),
    )
    page.initialize_catalogs()
    assert page.create_subject() is True
    page.subject_table.setCurrentCell(0, 0)
    assert page.edit_subject() is True
    assert page.toggle_subject_active() is True
    assert ("create_subject", "ART", "Art", True) in service.writes
    assert ("update_subject", 1, "SCI2", "New Science", False) in service.writes
    assert service.writes[-1] == ("set_subject_active", 1, False)


def test_assessment_actions_pass_database_ids_and_preserve_identity():
    app()
    service = ServiceStub()
    values = (1, 10, "New test", 1, "QUIZ", date(2026, 11, 1), AssessmentStatus.ACTIVE)
    page = CatalogPage(
        service,
        assessment_dialog_factory=lambda *_args: AcceptedDialog(values),
    )
    page.initialize_catalogs()
    assert page.create_assessment() is True
    page.assessment_table.setCurrentCell(0, 0)
    assert page.edit_assessment() is True
    assert page.toggle_assessment_active() is True
    assert ("create_assessment", *values[:-1]) in service.writes
    assert ("update_assessment", 100, *values) in service.writes
    assert service.writes[-1] == ("set_assessment_active", 100, False)


def test_support_rule_actions_keep_scope_ids_and_decimal_text_for_service_validation():
    app()
    service = ServiceStub()
    values = (1, 10, "4.75", True)
    page = CatalogPage(
        service,
        support_rule_dialog_factory=lambda *_args: AcceptedDialog(values),
    )
    page.initialize_catalogs()
    assert page.create_support_rule() is True
    page.rule_table.setCurrentCell(0, 0)
    assert page.edit_support_rule() is True
    assert page.toggle_support_rule_active() is True
    assert ("create_rule", *values) in service.writes
    assert ("update_rule", 5, "4.75") in service.writes
    assert service.writes[-1] == ("set_rule_active", 5, False)


def test_catalog_dialogs_store_fk_ids_and_lock_rule_scope_on_edit():
    app()
    service = ServiceStub()
    subject_dialog = SubjectDialog(service.subjects[0])
    assessment_dialog = AssessmentDialog(
        service.years, service.subjects, service.assessments[0]
    )
    rule_dialog = SupportRuleDialog(service.years, service.subjects, service.rules[0])
    assert subject_dialog.values() == ("SCI", "Science", True)
    assert assessment_dialog.values()[:2] == (1, 10)
    assert assessment_dialog.values()[-1] == AssessmentStatus.ACTIVE
    assert rule_dialog.values() == (1, 10, "4.25", True)
    assert not rule_dialog.school_year_combo.isEnabled()
    assert not rule_dialog.subject_combo.isEnabled()


def test_catalog_academic_ui_has_no_sql_repository_or_transaction_access():
    source = (
        inspect.getsource(inspect.getmodule(CatalogPage))
        + inspect.getsource(inspect.getmodule(SubjectDialog))
    ).upper()
    for forbidden in ("SELECT ", "INSERT ", "UPDATE ", "DELETE ", "REPOSITORY", "TRANSACTION"):
        assert forbidden not in source


def test_catalog_table_rows_keep_database_identity_in_user_role():
    app()
    page = CatalogPage(ServiceStub())
    page.initialize_catalogs()
    assert page.subject_table.item(0, 0).data(Qt.ItemDataRole.UserRole) == 1
    assert page.assessment_table.item(0, 0).data(Qt.ItemDataRole.UserRole) == 100
    assert page.rule_table.item(0, 0).data(Qt.ItemDataRole.UserRole) == 5
