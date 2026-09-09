from __future__ import annotations

import inspect
import os
from datetime import date, datetime
from decimal import Decimal

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QFrame, QGridLayout

from models.dto import Assessment, SchoolYear, ScoreRosterItem, Subject
from models.enums import AssessmentStatus
from tests.test_scores_page_manual_entry import (
    EnrollmentStub,
    ScoreStub,
    complete_context,
    make_page,
)
from tests.test_step_13_score_import_ui import valid_preview
from ui import theme
from ui.dialogs.catalog_dialogs import AssessmentDialog
from ui.dialogs.score_import_preview_dialog import ScoreImportPreviewDialog
from ui.pages.scores_page import ScoresPage
from ui.widgets.score_context_filter_widget import ScoreContextFilterWidget


def app() -> QApplication:
    return QApplication.instance() or QApplication([])


def assessment(status=AssessmentStatus.ACTIVE, assessment_id=101):
    return Assessment(
        assessment_id,
        11,
        2,
        "Giữa kỳ",
        1,
        "MIDTERM",
        date(2026, 10, 10),
        status,
        datetime(2026, 9, 1),
    )


class MixedAssessmentAcademic:
    def list_school_years(self):
        return [(2, "2026-2027", None, None, True)]

    def list_grades(self):
        return [(6, 6, "Khối 6")]

    def list_classes_by_school_year(self, _year_id):
        return [(61, "6A1", 6, None, True)]

    def list_active_subjects(self):
        return [(11, "M1", "Môn 1")]

    def list_assessments(self, _year_id, subject_id=None):
        return [
            assessment(AssessmentStatus.ACTIVE, 101),
            assessment(AssessmentStatus.LOCKED, 102),
            assessment(AssessmentStatus.CANCELLED, 103),
        ]


def select(combo, value):
    index = combo.findData(value)
    assert index >= 0
    combo.setCurrentIndex(index)


def test_scores_theme_and_page_cards_use_shared_design_system():
    app()
    page = ScoresPage()
    stylesheet = theme.scores_page_stylesheet()

    assert "QWidget#scoresPage" in stylesheet
    assert "QFrame#scoresToolbarCard" in stylesheet
    assert isinstance(page.toolbar_card, QFrame)
    assert isinstance(page.assessment_info_card, QFrame)
    assert page.title_label.isHidden()
    assert theme.APP_BACKGROUND in page.styleSheet()


def test_score_context_filter_uses_compact_grid_and_keeps_dependencies():
    app()
    widget = ScoreContextFilterWidget(MixedAssessmentAcademic())
    widget.load_options()

    assert isinstance(widget.layout(), QGridLayout)
    assert widget.grade_combo.isEnabled()
    assert widget.class_combo.isEnabled() is False
    select(widget.grade_combo, 6)
    assert widget.class_combo.isEnabled()
    select(widget.class_combo, 61)
    assert widget.subject_combo.isEnabled()


def test_locked_and_cancelled_assessments_remain_excluded_from_score_selector():
    app()
    page = ScoresPage(academic_service=MixedAssessmentAcademic())
    page.initialize_scores()
    select(page.grade_combo, 6)
    select(page.class_combo, 61)
    select(page.subject_combo, 11)

    assert page.assessment_combo.count() == 2
    assert page.assessment_combo.itemData(1) == 101
    assert page.assessment_combo.findData(102) == -1
    assert page.assessment_combo.findData(103) == -1


def test_selected_assessment_card_uses_loaded_metadata_without_extra_query():
    app()
    service = MixedAssessmentAcademic()
    page = ScoresPage(academic_service=service)
    page.initialize_scores()
    select(page.grade_combo, 6)
    select(page.class_combo, 61)
    select(page.subject_combo, 11)
    select(page.assessment_combo, 101)

    assert page.assessment_name_label.text() == "Giữa kỳ"
    assert "Môn 1" in page.assessment_meta_label.text()
    assert "10/10/2026" in page.assessment_meta_label.text()
    assert page.assessment_status_label.text() == "Đang mở"
    assert page.assessment_status_label.property("assessmentStatus") == "ACTIVE"


def test_score_table_is_compact_dark_and_renders_saved_status_badge():
    app()
    page = ScoresPage()
    page.set_score_rows((
        ScoreRosterItem(
            701,
            "student-1",
            "HS001",
            "Nguyễn Văn An",
            101,
            9001,
            Decimal("8.50"),
        ),
    ))

    assert page.score_table.objectName() == "scoreEntryTable"
    assert page.score_table.showGrid() is False
    assert page.score_table.verticalHeader().defaultSectionSize() == 40
    assert page.score_table.item(0, 2).text() == "Nguyễn Văn An"
    assert page.score_table.item(0, 4).text() == "Đã có điểm"
    assert (
        page.score_table.item(0, 4).foreground().color().name().upper()
        == theme.SUCCESS
    )


def test_incomplete_and_empty_roster_states_are_explicit():
    app()
    page = ScoresPage()
    assert page.placeholder_label.text() == (
        "Chọn bài đánh giá để xem hoặc nhập điểm."
    )

    empty_page = make_page(EnrollmentStub(result=[]), ScoreStub())
    complete_context(empty_page)
    assert empty_page.placeholder_label.text() == (
        "Chưa có học sinh trong phạm vi đã chọn."
    )
    assert empty_page.score_table.isHidden()


def test_manual_score_dirty_state_and_existing_save_gate_are_visible():
    app()
    page = make_page(EnrollmentStub(), ScoreStub())
    complete_context(page)

    assert page.save_button.isEnabled() is False
    assert page.unsaved_label.isHidden()
    page.score_table.item(0, 3).setText("7.25")

    assert page.save_button.isEnabled()
    assert not page.unsaved_label.isHidden()
    assert page.unsaved_label.text() == "Có thay đổi chưa lưu"
    assert page.save_button.property("variant") == "primary"


def test_score_validation_and_retry_semantics_are_unchanged():
    app()
    scores = ScoreStub()
    page = make_page(EnrollmentStub(), scores)
    complete_context(page)
    page.score_table.item(0, 3).setText("10.01")

    assert page.save_scores() is False
    assert scores.calls == []
    assert page.score_table.item(0, 3).text() == "10.01"
    assert page.context_status_label.text() == "Điểm nhập vào không hợp lệ."


def test_import_preview_dark_table_shows_valid_and_invalid_text_statuses():
    app()
    valid_dialog = ScoreImportPreviewDialog(valid_preview())
    invalid_dialog = ScoreImportPreviewDialog(valid_preview(invalid=True))

    assert valid_dialog.summary_card.property("dialogCard") is True
    assert valid_dialog.table.showGrid() is False
    assert valid_dialog.table.verticalHeader().defaultSectionSize() == 40
    assert valid_dialog.table.item(0, 5).text() == "Hợp lệ"
    assert invalid_dialog.table.item(0, 5).text() == "Lỗi"
    assert "Điểm lỗi" in invalid_dialog.table.item(0, 6).text()
    assert invalid_dialog.import_button.isEnabled() is False


def test_assessment_dialog_is_modernized_without_changing_enum_values():
    app()
    dialog = AssessmentDialog(
        [SchoolYear(2, "2026-2027", None, None, True)],
        [Subject(11, "M1", "Môn 1", True)],
    )

    assert dialog.objectName() == "assessmentDialog"
    assert dialog.form_card.property("dialogCard") is True
    assert dialog.save_button.property("variant") == "primary"
    assert [dialog.status_combo.itemData(index) for index in range(3)] == [
        AssessmentStatus.ACTIVE,
        AssessmentStatus.LOCKED,
        AssessmentStatus.CANCELLED,
    ]
    assert dialog.values()[0:2] == (11, 2)


def test_excel_actions_keep_existing_permission_guard_and_hierarchy():
    app()
    denied = ScoresPage(excel_permission_check=lambda: False)

    assert denied.import_excel_button.isHidden()
    assert denied.download_template_button.isHidden()
    assert denied.export_button.isHidden()
    assert denied.import_excel_button.isEnabled() is False


def test_scores_presentation_contains_no_threshold_transaction_or_data_layer():
    source = "\n".join(
        inspect.getsource(component)
        for component in (
            ScoresPage,
            ScoreContextFilterWidget,
            ScoreImportPreviewDialog,
            AssessmentDialog,
        )
    ).upper()

    assert "3.5" not in source
    assert ".TRANSACTION(" not in source
    assert "REPOSITORY" not in source
    assert "SELECT " not in source
    assert "INSERT " not in source
