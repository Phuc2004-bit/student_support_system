from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
import inspect
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QDialog, QMessageBox
import pytest

from bootstrap import build_app_context
from models.dto import Assessment, EnrollmentListItem, ScoreRosterItem
from models.dto.score_import import (
    ScoreImportContext,
    ScoreImportIssue,
    ScoreImportIssueSeverity,
    ScoreImportPreview,
    ScoreImportPreviewRow,
    ScoreImportSourceMetadata,
    ScoreImportTransactionResult,
    ScoreImportWorkbook,
)
from models.enums import AssessmentStatus, EnrollmentStatus
from services.score_import_commit_service import ScoreImportCommitService
from services.score_import_parser import ScoreImportWorkbookParser
from services.score_import_preview_service import ScoreImportPreviewService
from services.score_import_template_service import ScoreImportTemplateService
from ui.dialogs.score_import_preview_dialog import ScoreImportPreviewDialog
from ui.pages.scores_page import ScoresPage


NOW = datetime(2026, 9, 6)


def app():
    return QApplication.instance() or QApplication([])


class AcademicStub:
    def list_school_years(self):
        return [(2, "2026-2027", None, None, True)]

    def list_grades(self):
        return [(6, 6, "Khối 6")]

    def list_classes_by_school_year(self, _year_id):
        return [(61, "6A1", 6, None, True)]

    def list_active_subjects(self):
        return [(11, "M1", "Môn 1")]

    def list_active_assessments(self, year_id, subject_id=None, semester=None):
        return [Assessment(
            101, subject_id, year_id, "Giữa kỳ", 1, "MIDTERM",
            date(2026, 10, 10), AssessmentStatus.ACTIVE, NOW,
        )]


def enrollment(enrollment_id=701):
    return EnrollmentListItem(
        enrollment_id, f"student-{enrollment_id}", "HS01", "Học sinh 1",
        61, "6A1", 6, 2, "2026-2027", EnrollmentStatus.ACTIVE,
    )


class EnrollmentStub:
    def __init__(self, error=None):
        self.error = error
        self.calls = []

    def list_class_enrollments(self, class_id, year_id):
        self.calls.append((class_id, year_id))
        if self.error:
            raise self.error
        return [enrollment()]


class ScoreStub:
    def __init__(self):
        self.calls = []

    def list_score_roster(self, class_id, year_id, subject_id, assessment_id):
        self.calls.append((class_id, year_id, subject_id, assessment_id))
        return [ScoreRosterItem(701, "student-701", "HS01", "Học sinh 1", 101, None, None)]


class ParserStub:
    def __init__(self, result=None, error=None):
        self.result = result or ScoreImportWorkbook(
            "scores.xlsx", "Nhập điểm", ScoreImportSourceMetadata(), ()
        )
        self.error = error
        self.calls = []

    def parse_workbook(self, path):
        self.calls.append(path)
        if self.error:
            raise self.error
        return self.result


class PreviewStub:
    def __init__(self, result, error=None):
        self.result = result
        self.error = error
        self.calls = []

    def preview_import(self, selected, workbook):
        self.calls.append((selected, workbook))
        if self.error:
            raise self.error
        return self.result


class TemplateStub:
    def __init__(self, error=None):
        self.error = error
        self.calls = []

    def create_template(self, selected, roster, path):
        self.calls.append((selected, tuple(roster), path))
        if self.error:
            raise self.error


class CommitStub:
    def __init__(self, error=None):
        self.error = error
        self.calls = []

    def commit_import(self, value):
        self.calls.append(value)
        if self.error:
            raise self.error
        return ScoreImportTransactionResult(101, 1, 2, (901,), (801, 802))


def valid_preview(*, warning=False, invalid=False):
    issues = ()
    if warning:
        issues = (ScoreImportIssue(
            "NAME", "student_name", "Tên khác",
            ScoreImportIssueSeverity.WARNING,
        ),)
    if invalid:
        issues = (ScoreImportIssue("BAD", "score", "Điểm lỗi"),)
    return ScoreImportPreview(
        ScoreImportContext(2, "2026-2027", 61, "6A1", 11, "Môn 1", 101, "Giữa kỳ"),
        (ScoreImportPreviewRow(7, "student-701", "Excel Name", "Học sinh 1", 701, Decimal("8"), issues),),
    )


def select(combo, value):
    index = combo.findData(value)
    assert index >= 0
    combo.setCurrentIndex(index)


def complete_context(page):
    page.initialize_scores()
    select(page.grade_combo, 6)
    select(page.class_combo, 61)
    select(page.subject_combo, 11)
    select(page.assessment_combo, 101)


def make_page(*, preview_result=None, parser_error=None, preview_error=None, template_error=None, commit_error=None):
    app()
    workbook = ScoreImportWorkbook("scores.xlsx", "Nhập điểm", ScoreImportSourceMetadata(), ())
    parser = ParserStub(workbook, parser_error)
    preview_service = PreviewStub(preview_result or valid_preview(), preview_error)
    template = TemplateStub(template_error)
    commit = CommitStub(commit_error)
    enrollments = EnrollmentStub()
    scores = ScoreStub()
    page = ScoresPage(
        academic_service=AcademicStub(), enrollment_service=enrollments,
        score_service=scores, score_import_parser=parser,
        score_import_template_service=template,
        score_import_preview_service=preview_service,
        score_import_commit_service=commit,
    )
    return page, parser, preview_service, template, commit, enrollments, scores


def test_scores_page_has_excel_import_and_template_actions():
    page, *_ = make_page()
    assert page.import_excel_button.text() == "Nhập điểm từ Excel"
    assert page.download_template_button.text() == "Tải file mẫu"


@pytest.mark.parametrize("missing", ["year", "grade", "class", "subject", "assessment"])
def test_incomplete_context_blocks_import_and_template(missing):
    page, parser, _preview, template, commit, *_ = make_page()
    complete_context(page)
    combo = {
        "year": page.school_year_combo,
        "grade": page.grade_combo,
        "class": page.class_combo,
        "subject": page.subject_combo,
        "assessment": page.assessment_combo,
    }[missing]
    combo.setCurrentIndex(0)
    assert page.import_scores_from_excel() is False
    assert page.download_import_template() is False
    assert parser.calls == []
    assert template.calls == []
    assert commit.calls == []


def test_import_context_uses_selected_ids_and_labels():
    page, *_ = make_page(); complete_context(page)
    selected = page.score_import_context()
    assert (selected.school_year_id, selected.class_id, selected.subject_id, selected.assessment_id) == (2, 61, 11, 101)
    assert (selected.school_year_name, selected.class_name, selected.subject_name, selected.assessment_name) == ("2026-2027", "6A1", "Môn 1", "Giữa kỳ")


def test_cancel_template_destination_does_not_read_roster_or_create_file(monkeypatch):
    page, _parser, _preview, template, _commit, enrollments, _scores = make_page()
    complete_context(page)
    monkeypatch.setattr("ui.pages.scores_page.QFileDialog.getSaveFileName", lambda *_args: ("", ""))
    assert page.download_import_template() is False
    assert enrollments.calls == []
    assert template.calls == []


def test_template_uses_selected_class_roster_and_injected_service(monkeypatch):
    page, _parser, _preview, template, _commit, enrollments, _scores = make_page()
    complete_context(page)
    monkeypatch.setattr("ui.pages.scores_page.QFileDialog.getSaveFileName", lambda *_args: ("template.xlsx", ""))
    monkeypatch.setattr("ui.pages.scores_page.QMessageBox.information", lambda *_args: None)
    assert page.download_import_template() is True
    assert enrollments.calls[-1] == (61, 2)
    selected, roster, path = template.calls[0]
    assert path == "template.xlsx"
    assert selected.assessment_id == 101
    assert [(item.student_id, item.full_name) for item in roster] == [("student-701", "Học sinh 1")]


def test_template_error_is_displayed_without_success(monkeypatch):
    page, *_ = make_page(template_error=RuntimeError("template failed"))
    complete_context(page)
    shown = []
    monkeypatch.setattr("ui.pages.scores_page.QFileDialog.getSaveFileName", lambda *_args: ("template.xlsx", ""))
    monkeypatch.setattr("ui.pages.scores_page.QMessageBox.warning", lambda *args: shown.append(args))
    assert page.download_import_template() is False
    assert "template failed" in page.context_status_label.text()
    assert len(shown) == 1


def test_cancel_open_file_does_not_parse_preview_or_commit(monkeypatch):
    page, parser, preview_service, _template, commit, *_ = make_page(); complete_context(page)
    monkeypatch.setattr("ui.pages.scores_page.QFileDialog.getOpenFileName", lambda *_args: ("", ""))
    assert page.import_scores_from_excel() is False
    assert parser.calls == []
    assert preview_service.calls == []
    assert commit.calls == []


def test_parser_error_stops_before_preview_and_commit(monkeypatch):
    page, parser, preview_service, _template, commit, *_ = make_page(parser_error=RuntimeError("bad workbook"))
    complete_context(page)
    monkeypatch.setattr("ui.pages.scores_page.QFileDialog.getOpenFileName", lambda *_args: ("scores.xlsx", ""))
    monkeypatch.setattr("ui.pages.scores_page.QMessageBox.warning", lambda *_args: None)
    assert page.import_scores_from_excel() is False
    assert parser.calls == ["scores.xlsx"]
    assert preview_service.calls == []
    assert commit.calls == []


@pytest.mark.parametrize(
    ("preview_value", "status", "enabled"),
    [(valid_preview(), "Hợp lệ", True), (valid_preview(warning=True), "Cảnh báo", True), (valid_preview(invalid=True), "Lỗi", False)],
)
def test_preview_dialog_renders_status_summary_and_commit_gate(preview_value, status, enabled):
    app(); dialog = ScoreImportPreviewDialog(preview_value)
    assert dialog.table.rowCount() == 1
    assert dialog.table.item(0, 5).text() == status
    assert dialog.import_button.isEnabled() is enabled
    assert f"Hợp lệ: {preview_value.valid_count}" in dialog.summary_label.text()
    assert f"Lỗi: {preview_value.invalid_count}" in dialog.summary_label.text()


def prepare_import(monkeypatch, page, *, confirm=QMessageBox.StandardButton.Yes):
    complete_context(page)
    monkeypatch.setattr("ui.pages.scores_page.QFileDialog.getOpenFileName", lambda *_args: ("scores.xlsx", ""))
    monkeypatch.setattr("ui.pages.scores_page.ScoreImportPreviewDialog.exec", lambda _self: QDialog.DialogCode.Accepted)
    monkeypatch.setattr("ui.pages.scores_page.QMessageBox.question", lambda *_args: confirm)


def test_metadata_never_overrides_selected_context_and_cancel_confirm_does_not_commit(monkeypatch):
    page, parser, preview_service, _template, commit, *_ = make_page()
    parser.result = ScoreImportWorkbook("x.xlsx", "Nhập điểm", ScoreImportSourceMetadata("other", "other", "other", "other"), ())
    prepare_import(monkeypatch, page, confirm=QMessageBox.StandardButton.No)
    assert page.import_scores_from_excel() is False
    selected = preview_service.calls[0][0]
    assert (selected.school_year_id, selected.class_id, selected.subject_id, selected.assessment_id) == (2, 61, 11, 101)
    assert commit.calls == []


def test_invalid_preview_cannot_reach_confirmation_or_commit(monkeypatch):
    page, _parser, _preview, _template, commit, *_ = make_page(preview_result=valid_preview(invalid=True))
    questions = []
    prepare_import(monkeypatch, page)
    monkeypatch.setattr("ui.pages.scores_page.QMessageBox.question", lambda *args: questions.append(args))
    monkeypatch.setattr("ui.pages.scores_page.QMessageBox.warning", lambda *_args: None)
    assert page.import_scores_from_excel() is False
    assert questions == []
    assert commit.calls == []


def test_valid_confirmation_commits_once_shows_result_and_refreshes_context(monkeypatch):
    page, parser, preview_service, _template, commit, _enrollments, scores = make_page()
    prepare_import(monkeypatch, page)
    messages = []
    monkeypatch.setattr("ui.pages.scores_page.QMessageBox.information", lambda *args: messages.append(args))
    before_loads = len(scores.calls)
    assert page.import_scores_from_excel() is True
    assert parser.calls == ["scores.xlsx"]
    assert len(preview_service.calls) == 1
    assert commit.calls == [preview_service.result]
    assert len(scores.calls) == before_loads + 1
    assert page.current_context().assessment_id == 101
    assert "Đã nhập 1 điểm" in messages[0][2]
    assert "Phát hiện 2 ca" in messages[0][2]


def test_commit_error_shows_no_success_and_keeps_context(monkeypatch):
    page, _parser, _preview, _template, commit, _enrollments, scores = make_page(commit_error=RuntimeError("preview stale"))
    prepare_import(monkeypatch, page)
    warnings, success = [], []
    monkeypatch.setattr("ui.pages.scores_page.QMessageBox.warning", lambda *args: warnings.append(args))
    monkeypatch.setattr("ui.pages.scores_page.QMessageBox.information", lambda *args: success.append(args))
    before_loads = len(scores.calls)
    assert page.import_scores_from_excel() is False
    assert len(commit.calls) == 1
    assert len(scores.calls) == before_loads
    assert warnings and not success
    assert page.current_context().assessment_id == 101


def test_bootstrap_composes_and_shares_import_dependencies():
    context = build_app_context()
    assert isinstance(context.score_import_parser, ScoreImportWorkbookParser)
    assert isinstance(context.score_import_template_service, ScoreImportTemplateService)
    assert isinstance(context.score_import_preview_service, ScoreImportPreviewService)
    assert isinstance(context.score_import_commit_service, ScoreImportCommitService)
    assert context.score_import_commit_service.preview_service is context.score_import_preview_service
    assert context.score_import_commit_service.score_service is context.score_service


def test_import_ui_has_no_repository_sql_transaction_or_support_workflow_logic():
    source = (
        inspect.getsource(ScoresPage)
        + inspect.getsource(ScoreImportPreviewDialog)
    ).upper()
    for forbidden in (
        "REPOSITORY", "SELECT ", "INSERT ", "UPDATE DBO", "DELETE ",
        ".TRANSACTION(", "SUPPORTSERVICE", "CREATE_INTERVENTION",
        "CREATE_REVIEW", "WAITING_REVIEW", "AUTO COMPLETE",
    ):
        assert forbidden not in source
