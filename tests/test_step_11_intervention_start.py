from contextlib import contextmanager
from dataclasses import replace
from datetime import date
import inspect
import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox

from exceptions import InvalidStateTransitionError
from models.enums import InterventionStatus, UserRole
from repositories import InterventionRepository, UserRepository
from services.report_service import ReportService
from services.support_service import SupportService
from ui.dialogs.intervention_detail_dialog import InterventionDetailDialog
from ui.dialogs.intervention_start_confirmation import (
    confirm_begin_support,
)
from ui.pages.support_page import SupportPage
from tests.test_report_repository_integration import (
    cleanup,
    get_test_db,
    seed_report_data,
)
from tests.test_step_11_intervention_detail import detail, report_row


TEST_USERNAME = "s115_teacher"


def app():
    return QApplication.instance() or QApplication([])


class StartServiceStub:
    def __init__(self):
        self.calls = []
        self.fail = False

    def start_intervention(self, intervention_id):
        self.calls.append(intervention_id)
        if self.fail:
            raise RuntimeError("raw database error")
        return SimpleNamespace(intervention_id=intervention_id)


@pytest.mark.parametrize(
    ("status", "visible"),
    [
        (InterventionStatus.DETECTED, False),
        (InterventionStatus.PLANNED, True),
        (InterventionStatus.IN_PROGRESS, False),
        (InterventionStatus.WAITING_REVIEW, False),
        (InterventionStatus.CONTINUE, False),
        (InterventionStatus.COMPLETED, False),
    ],
)
def test_start_action_is_available_only_for_planned(status, visible):
    app()
    value = replace(detail(), status=status)
    dialog = InterventionDetailDialog(
        101,
        SimpleNamespace(get_intervention_detail=lambda _id: value),
        start_service=StartServiceStub(),
    )

    dialog.load_detail()

    assert dialog.start_button.text() == "Bắt đầu bổ trợ"
    assert dialog.start_button.isHidden() is (not visible)
    assert dialog.start_button.isEnabled() is visible


def test_confirmation_cancel_does_not_call_service(monkeypatch):
    app()
    service = StartServiceStub()
    monkeypatch.setattr(
        "ui.dialogs.intervention_start_confirmation.QMessageBox.question",
        lambda *_args, **_kwargs: QMessageBox.StandardButton.No,
    )

    assert confirm_begin_support(None, service, 101) is False
    assert service.calls == []


def test_confirmation_accept_calls_production_contract(monkeypatch):
    app()
    service = StartServiceStub()
    monkeypatch.setattr(
        "ui.dialogs.intervention_start_confirmation.QMessageBox.question",
        lambda *_args, **_kwargs: QMessageBox.StandardButton.Yes,
    )

    assert confirm_begin_support(None, service, 101) is True
    assert service.calls == [101]


def test_cancel_confirmation_keeps_loaded_detail_without_refresh():
    app()
    planned = replace(detail(), status=InterventionStatus.PLANNED)

    class Reader:
        def __init__(self):
            self.calls = []

        def get_intervention_detail(self, intervention_id):
            self.calls.append(intervention_id)
            return planned

    reader = Reader()
    service = StartServiceStub()
    dialog = InterventionDetailDialog(
        101,
        reader,
        start_service=service,
        start_confirmation=lambda *_args: False,
    )
    dialog.load_detail()

    assert dialog.begin_planned_support() is False
    assert reader.calls == [101]
    assert service.calls == []
    assert dialog.detail.status is InterventionStatus.PLANNED


def test_successful_start_refreshes_detail_and_hides_action():
    app()
    planned = replace(detail(), status=InterventionStatus.PLANNED)
    in_progress = replace(
        planned,
        status=InterventionStatus.IN_PROGRESS,
    )

    class Reader:
        def __init__(self):
            self.values = [planned, in_progress]
            self.calls = []

        def get_intervention_detail(self, intervention_id):
            self.calls.append(intervention_id)
            return self.values.pop(0)

    reader = Reader()
    service = StartServiceStub()

    def confirm(_parent, start_service, intervention_id):
        start_service.start_intervention(intervention_id)
        return True

    dialog = InterventionDetailDialog(
        101,
        reader,
        start_service=service,
        start_confirmation=confirm,
    )
    emitted = []
    dialog.intervention_started.connect(emitted.append)
    dialog.load_detail()

    assert dialog.begin_planned_support() is True
    assert service.calls == [101]
    assert reader.calls == [101, 101]
    assert dialog.detail.status is InterventionStatus.IN_PROGRESS
    assert dialog.status_value_label.text() == "Đang bổ trợ"
    assert dialog.start_button.isHidden()
    assert dialog.plan_button.isHidden()
    assert emitted == [101]


def test_start_failure_is_normalized_and_does_not_refresh():
    app()
    planned = replace(detail(), status=InterventionStatus.PLANNED)

    class Reader:
        def __init__(self):
            self.calls = []

        def get_intervention_detail(self, intervention_id):
            self.calls.append(intervention_id)
            return planned

    reader = Reader()
    service = StartServiceStub()
    service.fail = True

    def confirm(_parent, start_service, intervention_id):
        start_service.start_intervention(intervention_id)
        return True

    dialog = InterventionDetailDialog(
        101,
        reader,
        start_service=service,
        start_confirmation=confirm,
    )
    dialog.load_detail()

    assert dialog.begin_planned_support() is False
    assert reader.calls == [101]
    assert "raw database error" not in dialog.error_label.text()
    assert dialog.detail.status is InterventionStatus.PLANNED


class SimpleSignal:
    def __init__(self):
        self.callback = None

    def connect(self, callback):
        self.callback = callback

    def emit(self, value):
        self.callback(value)


class DetailDialogThatStarts:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.intervention_started = SimpleSignal()

    def load_detail(self):
        return None

    def exec(self):
        self.intervention_started.emit(731)
        return 0


@pytest.mark.parametrize(
    ("filter_status", "expected_rows"),
    [
        (InterventionStatus.PLANNED, 0),
        (None, 1),
        (InterventionStatus.IN_PROGRESS, 1),
    ],
)
def test_support_page_refreshes_matching_filter_after_start(
    filter_status,
    expected_rows,
):
    app()

    class Reader:
        def __init__(self):
            self.started = False

        def get_support_cases(self, status=None, **_filters):
            self.started = True
            row = report_row(731)
            row = replace(row, status="IN_PROGRESS")
            if status == InterventionStatus.PLANNED:
                return []
            return [row]

    reader = Reader()
    service = StartServiceStub()
    page = SupportPage(
        support_read_service=reader,
        intervention_detail_service=SimpleNamespace(),
        intervention_start_service=service,
        detail_dialog_factory=DetailDialogThatStarts,
    )
    page.school_year_combo.addItem("2026-2027", 2)
    page.school_year_combo.setCurrentIndex(1)
    if filter_status is not None:
        page.status_combo.addItem("filter", filter_status)
        page.status_combo.setCurrentIndex(
            page.status_combo.findData(filter_status)
        )

    assert page.open_intervention_detail(731) is True
    assert page.table.rowCount() == expected_rows
    if expected_rows:
        assert page.table.item(0, 8).text() == "Đang bổ trợ"


class FakeDatabase:
    def __init__(self):
        self.connection = object()
        self.transactions = 0

    @contextmanager
    def transaction(self):
        self.transactions += 1
        yield self.connection


@pytest.mark.parametrize(
    "status",
    [
        InterventionStatus.DETECTED,
        InterventionStatus.IN_PROGRESS,
        InterventionStatus.WAITING_REVIEW,
        InterventionStatus.CONTINUE,
        InterventionStatus.COMPLETED,
    ],
)
def test_start_service_blocks_every_non_planned_status(status):
    value = replace(detail(), status=status)

    class Repository:
        update_calls = 0

        def get_by_id(self, _connection, _intervention_id):
            return value

        def update_status(self, *_args):
            self.update_calls += 1

    repository = Repository()
    service = SupportService(
        FakeDatabase(),
        intervention_repository=repository,
    )

    with pytest.raises(InvalidStateTransitionError):
        service.start_intervention(101)

    assert repository.update_calls == 0


def test_start_service_updates_only_status_in_one_transaction():
    planned = replace(detail(), status=InterventionStatus.PLANNED)
    started = replace(planned, status=InterventionStatus.IN_PROGRESS)

    class Repository:
        def __init__(self):
            self.calls = []

        def get_by_id(self, connection, intervention_id):
            self.calls.append(("get", connection, intervention_id))
            return planned

        def update_status(self, connection, intervention_id, status):
            self.calls.append(
                ("update", connection, intervention_id, status)
            )
            return started

    db = FakeDatabase()
    repository = Repository()
    result = SupportService(
        db,
        intervention_repository=repository,
    ).start_intervention(101)

    assert result is started
    assert db.transactions == 1
    assert repository.calls == [
        ("get", db.connection, 101),
        ("update", db.connection, 101, InterventionStatus.IN_PROGRESS),
    ]


def cleanup_start_data(db):
    cleanup(db)
    with db.transaction() as connection:
        connection.cursor().execute(
            "DELETE FROM dbo.USERS WHERE username = ?",
            TEST_USERNAME,
        )


def test_real_planned_to_in_progress_is_atomic_and_preserves_data():
    db = get_test_db()
    cleanup_start_data(db)

    try:
        seeded = seed_report_data(db)
        repository = InterventionRepository()
        with db.transaction() as connection:
            teacher = UserRepository().create(
                connection,
                TEST_USERNAME,
                "hash",
                "Teacher Start Test",
                UserRole.TEACHER,
            )

        intervention_id = seeded["detected_intervention_id"]
        SupportService(db).plan_intervention(
            intervention_id,
            teacher.user_id,
            date(2026, 10, 15),
            "Học nhóm",
            "Giữ nguyên dữ liệu kế hoạch",
        )

        with db.transaction() as connection:
            planned = repository.get_by_id(connection, intervention_id)
            reviews_before = repository.list_reviews(
                connection,
                intervention_id,
            )
            cursor = connection.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM dbo.INTERVENTIONS"
            )
            intervention_count_before = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM dbo.SCORES")
            score_count_before = cursor.fetchone()[0]

        class FailingRepository(InterventionRepository):
            def update_status(self, *args, **kwargs):
                super().update_status(*args, **kwargs)
                raise RuntimeError("forced failure after update")

        with pytest.raises(RuntimeError):
            SupportService(
                db,
                intervention_repository=FailingRepository(),
            ).start_intervention(intervention_id)

        with db.transaction() as connection:
            after_failure = repository.get_by_id(
                connection,
                intervention_id,
            )
        assert after_failure.status is InterventionStatus.PLANNED

        started = SupportService(db).start_intervention(intervention_id)
        assert started.status is InterventionStatus.IN_PROGRESS

        with pytest.raises(InvalidStateTransitionError):
            SupportService(db).start_intervention(intervention_id)

        with db.transaction() as connection:
            saved = repository.get_by_id(connection, intervention_id)
            reviews_after = repository.list_reviews(
                connection,
                intervention_id,
            )
            cursor = connection.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM dbo.INTERVENTIONS"
            )
            intervention_count_after = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM dbo.SCORES")
            score_count_after = cursor.fetchone()[0]

        assert saved.intervention_id == planned.intervention_id
        assert saved.enrollment_id == planned.enrollment_id
        assert saved.subject_id == planned.subject_id
        assert saved.trigger_score_id == planned.trigger_score_id
        assert saved.responsible_user_id == planned.responsible_user_id
        assert saved.start_date == planned.start_date
        assert saved.support_method == planned.support_method
        assert saved.notes == planned.notes
        assert saved.detected_date == planned.detected_date
        assert reviews_after == reviews_before == []
        assert intervention_count_after == intervention_count_before
        assert score_count_after == score_count_before

        report = ReportService(db)
        planned_rows = report.get_support_cases(
            seeded["school_year_id"],
            status=InterventionStatus.PLANNED,
        )
        all_rows = report.get_support_cases(seeded["school_year_id"])
        in_progress_rows = report.get_support_cases(
            seeded["school_year_id"],
            status=InterventionStatus.IN_PROGRESS,
        )
        assert all(
            row.intervention_id != intervention_id
            for row in planned_rows
        )
        assert next(
            row for row in all_rows
            if row.intervention_id == intervention_id
        ).status == "IN_PROGRESS"
        assert any(
            row.intervention_id == intervention_id
            for row in in_progress_rows
        )
    finally:
        cleanup_start_data(db)


def test_start_ui_has_no_sql_or_direct_repository_access():
    modules = (
        inspect.getmodule(InterventionDetailDialog),
        inspect.getmodule(confirm_begin_support),
        inspect.getmodule(SupportPage),
    )
    source = "\n".join(inspect.getsource(module) for module in modules)
    upper_source = source.upper()

    for forbidden in (
        "SELECT ",
        "INSERT ",
        "UPDATE ",
        "DELETE ",
        "REPOSITORY",
        "MARK_WAITING_REVIEW",
        "CONTINUE_INTERVENTION",
        "REVIEW_INTERVENTION",
    ):
        assert forbidden not in upper_source
