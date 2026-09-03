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
from ui.dialogs.intervention_waiting_review_confirmation import (
    confirm_ready_for_review,
)
from ui.pages.support_page import SupportPage
from tests.test_report_repository_integration import (
    cleanup,
    get_test_db,
    seed_report_data,
)
from tests.test_step_11_intervention_detail import detail, report_row


TEST_USERNAME = "s116_teacher"


def app():
    return QApplication.instance() or QApplication([])


class WaitingReviewServiceStub:
    def __init__(self):
        self.calls = []
        self.fail = False

    def mark_waiting_review(self, intervention_id):
        self.calls.append(intervention_id)
        if self.fail:
            raise RuntimeError("raw database error")
        return SimpleNamespace(intervention_id=intervention_id)


@pytest.mark.parametrize(
    ("status", "visible"),
    [
        (InterventionStatus.DETECTED, False),
        (InterventionStatus.PLANNED, False),
        (InterventionStatus.IN_PROGRESS, True),
        (InterventionStatus.WAITING_REVIEW, False),
        (InterventionStatus.CONTINUE, False),
        (InterventionStatus.COMPLETED, False),
    ],
)
def test_waiting_review_action_is_available_only_for_in_progress(
    status,
    visible,
):
    app()
    value = replace(detail(), status=status)
    dialog = InterventionDetailDialog(
        101,
        SimpleNamespace(get_intervention_detail=lambda _id: value),
        waiting_review_service=WaitingReviewServiceStub(),
    )

    dialog.load_detail()

    assert dialog.waiting_review_button.text() == "Chuyển chờ đánh giá"
    assert dialog.waiting_review_button.isHidden() is (not visible)
    assert dialog.waiting_review_button.isEnabled() is visible


def test_waiting_review_confirmation_cancel_does_not_call_service(
    monkeypatch,
):
    app()
    service = WaitingReviewServiceStub()
    monkeypatch.setattr(
        "ui.dialogs.intervention_waiting_review_confirmation."
        "QMessageBox.question",
        lambda *_args, **_kwargs: QMessageBox.StandardButton.No,
    )

    assert confirm_ready_for_review(None, service, 101) is False
    assert service.calls == []


def test_waiting_review_confirmation_accept_calls_contract(monkeypatch):
    app()
    service = WaitingReviewServiceStub()
    monkeypatch.setattr(
        "ui.dialogs.intervention_waiting_review_confirmation."
        "QMessageBox.question",
        lambda *_args, **_kwargs: QMessageBox.StandardButton.Yes,
    )

    assert confirm_ready_for_review(None, service, 101) is True
    assert service.calls == [101]


def test_cancel_waiting_review_keeps_detail_without_refresh():
    app()
    in_progress = replace(detail(), status=InterventionStatus.IN_PROGRESS)

    class Reader:
        def __init__(self):
            self.calls = []

        def get_intervention_detail(self, intervention_id):
            self.calls.append(intervention_id)
            return in_progress

    reader = Reader()
    service = WaitingReviewServiceStub()
    dialog = InterventionDetailDialog(
        101,
        reader,
        waiting_review_service=service,
        waiting_review_confirmation=lambda *_args: False,
    )
    dialog.load_detail()

    assert dialog.move_to_review_queue() is False
    assert reader.calls == [101]
    assert service.calls == []
    assert dialog.detail.status is InterventionStatus.IN_PROGRESS


def test_successful_waiting_review_refreshes_detail_and_hides_action():
    app()
    in_progress = replace(detail(), status=InterventionStatus.IN_PROGRESS)
    waiting = replace(
        in_progress,
        status=InterventionStatus.WAITING_REVIEW,
    )

    class Reader:
        def __init__(self):
            self.values = [in_progress, waiting]
            self.calls = []

        def get_intervention_detail(self, intervention_id):
            self.calls.append(intervention_id)
            return self.values.pop(0)

    reader = Reader()
    service = WaitingReviewServiceStub()

    def confirm(_parent, waiting_service, intervention_id):
        waiting_service.mark_waiting_review(intervention_id)
        return True

    dialog = InterventionDetailDialog(
        101,
        reader,
        waiting_review_service=service,
        waiting_review_confirmation=confirm,
    )
    emitted = []
    dialog.intervention_waiting_review.connect(emitted.append)
    dialog.load_detail()

    assert dialog.move_to_review_queue() is True
    assert service.calls == [101]
    assert reader.calls == [101, 101]
    assert dialog.detail.status is InterventionStatus.WAITING_REVIEW
    assert dialog.status_value_label.text() == "Chờ đánh giá"
    assert dialog.waiting_review_button.isHidden()
    assert dialog.plan_button.isHidden()
    assert dialog.start_button.isHidden()
    assert emitted == [101]


def test_waiting_review_failure_is_normalized_and_retryable():
    app()
    in_progress = replace(detail(), status=InterventionStatus.IN_PROGRESS)

    class Reader:
        def __init__(self):
            self.calls = []

        def get_intervention_detail(self, intervention_id):
            self.calls.append(intervention_id)
            return in_progress

    reader = Reader()
    service = WaitingReviewServiceStub()
    service.fail = True

    def confirm(_parent, waiting_service, intervention_id):
        waiting_service.mark_waiting_review(intervention_id)
        return True

    dialog = InterventionDetailDialog(
        101,
        reader,
        waiting_review_service=service,
        waiting_review_confirmation=confirm,
    )
    dialog.load_detail()

    assert dialog.move_to_review_queue() is False
    assert reader.calls == [101]
    assert "raw database error" not in dialog.error_label.text()
    assert dialog.waiting_review_button.isEnabled()
    assert dialog.detail.status is InterventionStatus.IN_PROGRESS


class SimpleSignal:
    def __init__(self):
        self.callback = None

    def connect(self, callback):
        self.callback = callback

    def emit(self, value):
        self.callback(value)


class DetailDialogThatWaitsForReview:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.intervention_waiting_review = SimpleSignal()

    def load_detail(self):
        return None

    def exec(self):
        self.intervention_waiting_review.emit(731)
        return 0


@pytest.mark.parametrize(
    ("filter_status", "expected_rows"),
    [
        (InterventionStatus.IN_PROGRESS, 0),
        (None, 1),
        (InterventionStatus.WAITING_REVIEW, 1),
    ],
)
def test_support_page_refreshes_matching_filter_after_waiting_review(
    filter_status,
    expected_rows,
):
    app()

    class Reader:
        def get_support_cases(self, status=None, **_filters):
            row = replace(report_row(731), status="WAITING_REVIEW")
            if status == InterventionStatus.IN_PROGRESS:
                return []
            return [row]

    service = WaitingReviewServiceStub()
    page = SupportPage(
        support_read_service=Reader(),
        intervention_detail_service=SimpleNamespace(),
        intervention_waiting_review_service=service,
        detail_dialog_factory=DetailDialogThatWaitsForReview,
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
        assert page.table.item(0, 8).text() == "Chờ đánh giá"


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
        InterventionStatus.PLANNED,
        InterventionStatus.WAITING_REVIEW,
        InterventionStatus.CONTINUE,
        InterventionStatus.COMPLETED,
    ],
)
def test_waiting_review_service_blocks_every_non_in_progress_status(
    status,
):
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
        service.mark_waiting_review(101)

    assert repository.update_calls == 0


def test_waiting_review_service_updates_only_status_in_one_transaction():
    in_progress = replace(detail(), status=InterventionStatus.IN_PROGRESS)
    waiting = replace(
        in_progress,
        status=InterventionStatus.WAITING_REVIEW,
    )

    class Repository:
        def __init__(self):
            self.calls = []

        def get_by_id(self, connection, intervention_id):
            self.calls.append(("get", connection, intervention_id))
            return in_progress

        def update_status(self, connection, intervention_id, status):
            self.calls.append(
                ("update", connection, intervention_id, status)
            )
            return waiting

    db = FakeDatabase()
    repository = Repository()
    result = SupportService(
        db,
        intervention_repository=repository,
    ).mark_waiting_review(101)

    assert result is waiting
    assert db.transactions == 1
    assert repository.calls == [
        ("get", db.connection, 101),
        (
            "update",
            db.connection,
            101,
            InterventionStatus.WAITING_REVIEW,
        ),
    ]


def cleanup_waiting_review_data(db):
    cleanup(db)
    with db.transaction() as connection:
        connection.cursor().execute(
            "DELETE FROM dbo.USERS WHERE username = ?",
            TEST_USERNAME,
        )


def test_real_in_progress_to_waiting_review_is_atomic_and_preserves_data():
    db = get_test_db()
    cleanup_waiting_review_data(db)

    try:
        seeded = seed_report_data(db)
        repository = InterventionRepository()
        with db.transaction() as connection:
            teacher = UserRepository().create(
                connection,
                TEST_USERNAME,
                "hash",
                "Teacher Waiting Review Test",
                UserRole.TEACHER,
            )

        intervention_id = seeded["detected_intervention_id"]
        service = SupportService(db)
        service.plan_intervention(
            intervention_id,
            teacher.user_id,
            date(2026, 10, 15),
            "Học nhóm",
            "Giữ nguyên dữ liệu khi chờ đánh giá",
        )
        service.start_intervention(intervention_id)

        with db.transaction() as connection:
            in_progress = repository.get_by_id(
                connection,
                intervention_id,
            )
            reviews_before = repository.list_reviews(
                connection,
                intervention_id,
            )
            cursor = connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM dbo.INTERVENTIONS")
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
            ).mark_waiting_review(intervention_id)

        with db.transaction() as connection:
            after_failure = repository.get_by_id(
                connection,
                intervention_id,
            )
        assert after_failure.status is InterventionStatus.IN_PROGRESS

        waiting = service.mark_waiting_review(intervention_id)
        assert waiting.status is InterventionStatus.WAITING_REVIEW

        with pytest.raises(InvalidStateTransitionError):
            service.mark_waiting_review(intervention_id)

        with db.transaction() as connection:
            saved = repository.get_by_id(connection, intervention_id)
            reviews_after = repository.list_reviews(
                connection,
                intervention_id,
            )
            cursor = connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM dbo.INTERVENTIONS")
            intervention_count_after = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM dbo.SCORES")
            score_count_after = cursor.fetchone()[0]

        assert saved.intervention_id == in_progress.intervention_id
        assert saved.enrollment_id == in_progress.enrollment_id
        assert saved.subject_id == in_progress.subject_id
        assert saved.trigger_score_id == in_progress.trigger_score_id
        assert saved.responsible_user_id == in_progress.responsible_user_id
        assert saved.start_date == in_progress.start_date
        assert saved.support_method == in_progress.support_method
        assert saved.notes == in_progress.notes
        assert saved.detected_date == in_progress.detected_date
        assert reviews_after == reviews_before == []
        assert intervention_count_after == intervention_count_before
        assert score_count_after == score_count_before

        report = ReportService(db)
        in_progress_rows = report.get_support_cases(
            seeded["school_year_id"],
            status=InterventionStatus.IN_PROGRESS,
        )
        all_rows = report.get_support_cases(seeded["school_year_id"])
        waiting_rows = report.get_support_cases(
            seeded["school_year_id"],
            status=InterventionStatus.WAITING_REVIEW,
        )
        assert all(
            row.intervention_id != intervention_id
            for row in in_progress_rows
        )
        assert next(
            row for row in all_rows
            if row.intervention_id == intervention_id
        ).status == "WAITING_REVIEW"
        assert any(
            row.intervention_id == intervention_id
            for row in waiting_rows
        )
    finally:
        cleanup_waiting_review_data(db)


def test_waiting_review_ui_has_no_sql_or_direct_repository_access():
    modules = (
        inspect.getmodule(InterventionDetailDialog),
        inspect.getmodule(confirm_ready_for_review),
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
        "CONTINUE_INTERVENTION",
        "REVIEW_INTERVENTION",
    ):
        assert forbidden not in upper_source
