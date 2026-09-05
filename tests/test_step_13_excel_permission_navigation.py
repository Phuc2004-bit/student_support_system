from __future__ import annotations

import inspect
import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from app_context import AppContext
from bootstrap import build_app_context
from models.dto import UserSession
from models.enums import UserRole
from services.data_export_service import ScoreExportService, StudentExportService
from services.permission_service import PermissionService
from services.report_export_service import ReportExportService
from services.score_import_commit_service import ScoreImportCommitService
from services.score_import_parser import ScoreImportWorkbookParser
from services.score_import_preview_service import ScoreImportPreviewService
from services.score_import_template_service import ScoreImportTemplateService
from ui.main_window import MainWindow
from ui.pages.scores_page import ScoresPage


def app():
    return QApplication.instance() or QApplication([])


def session(role=UserRole.ADMIN, user_id=1):
    return UserSession(user_id, f"user{user_id}", "User", role)


class Recorder:
    def __init__(self):
        self.calls = []

    def export_xlsx(self, *args, **kwargs):
        self.calls.append(("export", args, kwargs))

    def parse_workbook(self, *args, **kwargs):
        self.calls.append(("parse", args, kwargs))
        return object()

    def create_template(self, *args, **kwargs):
        self.calls.append(("template", args, kwargs))

    def preview_import(self, *args, **kwargs):
        self.calls.append(("preview", args, kwargs))
        return SimpleNamespace(can_commit=True, valid_count=1)

    def commit_import(self, *args, **kwargs):
        self.calls.append(("commit", args, kwargs))
        return SimpleNamespace(imported_count=1, intervention_created_count=0)

    def get_support_report(self, **kwargs):
        self.calls.append(("report", (), kwargs))
        return object()


class DenyExcelPermissions(PermissionService):
    @staticmethod
    def can_manage_students(_session):
        return False

    @staticmethod
    def can_manage_scores(_session):
        return False

    @staticmethod
    def can_manage_support(_session):
        return False

    @staticmethod
    def can_view_reports(_session):
        return False


def context(role=UserRole.ADMIN, permission_service=None):
    student_export = Recorder()
    score_export = Recorder()
    parser = Recorder()
    template = Recorder()
    preview = Recorder()
    commit = Recorder()
    report_export = Recorder()
    report = Recorder()
    value = AppContext(
        db=object(),
        auth_service=object(),
        permission_service=permission_service or PermissionService(),
        session=session(role),
        student_export_service=student_export,
        score_export_service=score_export,
        score_import_parser=parser,
        score_import_template_service=template,
        score_import_preview_service=preview,
        score_import_commit_service=commit,
        report_export_service=report_export,
        report_service=report,
    )
    return value, {
        "student_export": student_export,
        "score_export": score_export,
        "parser": parser,
        "template": template,
        "preview": preview,
        "commit": commit,
        "report_export": report_export,
        "report": report,
    }


def excel_buttons(window):
    scores = window.pages["scores"]
    return (
        window.pages["students"].export_button,
        scores.download_template_button,
        scores.import_excel_button,
        scores.export_button,
        window.pages["support"].export_button,
        window.pages["reports"].export_button,
    )


@pytest.mark.parametrize("role", [UserRole.ADMIN, UserRole.TEACHER])
def test_real_policy_allows_excel_actions_for_both_supported_roles(role):
    app(); ctx, _recorders = context(role)
    window = MainWindow(ctx)
    assert all(not button.isHidden() and button.isEnabled() for button in excel_buttons(window))
    for key in ("students", "scores", "support", "reports"):
        assert window.can_navigate_to(key) is True


def test_excel_permissions_reuse_existing_page_policy_without_new_permission_method():
    admin = session(UserRole.ADMIN)
    teacher = session(UserRole.TEACHER)
    permission = PermissionService()
    checks = (
        permission.can_manage_students,
        permission.can_manage_scores,
        permission.can_manage_support,
        permission.can_view_reports,
    )
    assert all(check(admin) and check(teacher) for check in checks)
    source = inspect.getsource(PermissionService)
    assert "can_import_excel" not in source
    assert "can_export_excel" not in source


def test_denied_actor_has_hidden_disabled_actions_and_navigation_blocked():
    app(); ctx, _recorders = context(permission_service=DenyExcelPermissions())
    window = MainWindow(ctx)
    assert all(button.isHidden() and not button.isEnabled() for button in excel_buttons(window))
    for key in ("students", "scores", "support", "reports"):
        assert window.can_navigate_to(key) is False
        with pytest.raises(PermissionError):
            window.navigate_to(key)


def test_denied_programmatic_handlers_do_not_reach_excel_services(monkeypatch):
    app(); ctx, recorders = context(permission_service=DenyExcelPermissions())
    window = MainWindow(ctx)
    monkeypatch.setattr("ui.pages.students_page.QMessageBox.warning", lambda *_: None)
    monkeypatch.setattr("ui.pages.scores_page.QMessageBox.warning", lambda *_: None)
    monkeypatch.setattr("ui.pages.support_page.QMessageBox.warning", lambda *_: None)
    monkeypatch.setattr("ui.report_excel_actions.QMessageBox.warning", lambda *_: None)
    students = window.pages["students"]
    scores = window.pages["scores"]
    support = window.pages["support"]
    reports = window.pages["reports"]
    assert students.export_students() is False
    assert scores.download_import_template() is False
    assert scores.import_scores_from_excel() is False
    assert scores.export_scores() is False
    assert support.export_support_cases() is False
    assert reports.export_report() is False
    assert all(not recorder.calls for recorder in recorders.values())


def fill_score_context(page):
    for combo, label, value in (
        (page.school_year_combo, "2026-2027", 2),
        (page.grade_combo, "Khối 6", 6),
        (page.class_combo, "6A1", 61),
        (page.subject_combo, "Vật lý", 11),
        (page.assessment_combo, "Giữa kỳ", 101),
    ):
        combo.addItem(label, value)
        combo.setCurrentIndex(combo.count() - 1)


class AcceptedPreviewDialog:
    DialogCode = QDialog.DialogCode

    def __init__(self, *_args, **_kwargs):
        pass

    def exec(self):
        return self.DialogCode.Accepted


def test_score_import_rechecks_permission_immediately_before_commit(monkeypatch):
    app(); allowed = {"value": True}; parser = Recorder(); preview = Recorder(); commit = Recorder()
    page = ScoresPage(
        score_import_parser=parser,
        score_import_preview_service=preview,
        score_import_commit_service=commit,
        excel_permission_check=lambda: allowed["value"],
    )
    fill_score_context(page)
    monkeypatch.setattr("ui.pages.scores_page.QFileDialog.getOpenFileName", lambda *_: ("scores.xlsx", ""))
    monkeypatch.setattr("ui.pages.scores_page.ScoreImportPreviewDialog", AcceptedPreviewDialog)
    monkeypatch.setattr("ui.pages.scores_page.QMessageBox.warning", lambda *_: None)

    def revoke_before_commit(*_args):
        allowed["value"] = False
        return QMessageBox.StandardButton.Yes

    monkeypatch.setattr("ui.pages.scores_page.QMessageBox.question", revoke_before_commit)
    assert page.import_scores_from_excel() is False
    assert [call[0] for call in parser.calls] == ["parse"]
    assert [call[0] for call in preview.calls] == ["preview"]
    assert commit.calls == []


def test_preview_cancel_is_read_only_and_commit_remains_write_boundary(monkeypatch):
    app(); parser = Recorder(); preview = Recorder(); commit = Recorder()
    page = ScoresPage(
        score_import_parser=parser,
        score_import_preview_service=preview,
        score_import_commit_service=commit,
        excel_permission_check=lambda: True,
    )
    fill_score_context(page)
    monkeypatch.setattr("ui.pages.scores_page.QFileDialog.getOpenFileName", lambda *_: ("scores.xlsx", ""))

    class RejectedPreviewDialog(AcceptedPreviewDialog):
        def exec(self):
            return self.DialogCode.Rejected

    monkeypatch.setattr("ui.pages.scores_page.ScoreImportPreviewDialog", RejectedPreviewDialog)
    assert page.import_scores_from_excel() is False
    assert parser.calls and preview.calls
    assert commit.calls == []
    assert ".transaction(" in inspect.getsource(ScoreImportCommitService.commit_import)


def test_logout_invalidates_old_window_actions_and_navigation(monkeypatch):
    app(); ctx, recorders = context(UserRole.ADMIN); old_window = MainWindow(ctx)
    monkeypatch.setattr("ui.pages.students_page.QMessageBox.warning", lambda *_: None)
    old_window.request_logout()
    assert ctx.session is None
    assert old_window.can_navigate_to("students") is False
    assert old_window.pages["students"].export_students() is False
    assert recorders["student_export"].calls == []


def test_relogin_builds_new_action_guards_without_reactivating_old_window(monkeypatch):
    app(); ctx, recorders = context(UserRole.ADMIN); old_window = MainWindow(ctx)
    monkeypatch.setattr("ui.pages.students_page.QMessageBox.warning", lambda *_: None)
    ctx.clear_session()
    ctx.set_session(session(UserRole.TEACHER, user_id=2))
    new_window = MainWindow(ctx)
    assert old_window.can_navigate_to("students") is False
    assert old_window.pages["students"].export_students() is False
    assert all(not button.isHidden() and button.isEnabled() for button in excel_buttons(new_window))
    assert new_window.can_navigate_to("students") is True
    assert recorders["student_export"].calls == []


def test_bootstrap_constructs_each_excel_dependency_once_and_shares_instances():
    source = inspect.getsource(build_app_context)
    constructors = (
        "ScoreImportWorkbookParser()",
        "ScoreImportTemplateService()",
        "ScoreImportPreviewService(db=db)",
        "ScoreImportCommitService(",
        "StudentExportService(student_list_service)",
        "ScoreExportService(score_service)",
        "ReportExportService()",
    )
    assert all(source.count(constructor) == 1 for constructor in constructors)
    ctx = build_app_context()
    assert isinstance(ctx.score_import_parser, ScoreImportWorkbookParser)
    assert isinstance(ctx.score_import_template_service, ScoreImportTemplateService)
    assert isinstance(ctx.score_import_preview_service, ScoreImportPreviewService)
    assert isinstance(ctx.score_import_commit_service, ScoreImportCommitService)
    assert isinstance(ctx.student_export_service, StudentExportService)
    assert isinstance(ctx.score_export_service, ScoreExportService)
    assert isinstance(ctx.report_export_service, ReportExportService)


def test_no_excel_navigation_page_and_legacy_import_is_not_wired():
    keys = {key.lower() for key in MainWindow.PAGE_TITLES}
    assert not keys.intersection({"excel", "import", "export"})
    wiring = inspect.getsource(MainWindow) + inspect.getsource(build_app_context)
    assert "ImportService" not in wiring
    assert "import_service" not in wiring


def test_export_services_and_preview_remain_read_only():
    source = "\n".join((
        inspect.getsource(StudentExportService),
        inspect.getsource(ScoreExportService),
        inspect.getsource(ReportExportService),
        inspect.getsource(ScoreImportPreviewService.preview_import),
    )).upper()
    for forbidden in ("INSERT ", "UPDATE DBO", "DELETE ", ".COMMIT("):
        assert forbidden not in source


def test_excel_flows_do_not_reference_user_secrets():
    modules = (
        StudentExportService,
        ScoreExportService,
        ReportExportService,
        ScoreImportWorkbookParser,
        ScoreImportTemplateService,
        ScoreImportPreviewService,
        ScoreImportCommitService,
    )
    source = "\n".join(inspect.getsource(item) for item in modules).lower()
    assert "password_hash" not in source
    assert "plaintext_password" not in source
