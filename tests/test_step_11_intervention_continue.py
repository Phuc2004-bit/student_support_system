from contextlib import contextmanager
from dataclasses import replace
from datetime import date
from decimal import Decimal
import inspect
import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox

from exceptions import InvalidStateTransitionError, ValidationError
from models.enums import InterventionStatus, ReviewResult
from repositories import InterventionRepository, SupportRuleRepository
from services import ScoreService
from services.report_service import ReportService
from services.support_service import SupportService
from ui.dialogs.intervention_continue_confirmation import (
    confirm_continue_support,
)
from ui.dialogs.intervention_detail_dialog import InterventionDetailDialog
from ui.pages.support_page import SupportPage
from tests.test_report_repository_integration import (
    cleanup,
    get_test_db,
    seed_report_data,
)
from tests.test_step_11_intervention_detail import detail, report_row


def app():
    return QApplication.instance() or QApplication([])


def cleanup_continue_data(db):
    with db.transaction() as connection:
        connection.cursor().execute(
            """
            DELETE FROM dbo.SUPPORT_RULES
            WHERE subject_id IN
            (
                SELECT subject_id
                FROM dbo.SUBJECTS
                WHERE subject_code = ?
            )
            """,
            "TRPT_TOAN",
        )
    cleanup(db)


class ContinueServiceStub:
    def __init__(self):
        self.calls = []
        self.fail = False

    def continue_intervention(self, intervention_id):
        self.calls.append(intervention_id)
        if self.fail:
            raise RuntimeError("raw database error")
        return SimpleNamespace(
            intervention_id=intervention_id,
            status=InterventionStatus.IN_PROGRESS,
        )


@pytest.mark.parametrize(
    ("status", "visible"),
    [
        (InterventionStatus.DETECTED, False),
        (InterventionStatus.PLANNED, False),
        (InterventionStatus.IN_PROGRESS, False),
        (InterventionStatus.WAITING_REVIEW, False),
        (InterventionStatus.CONTINUE, True),
        (InterventionStatus.COMPLETED, False),
    ],
)
def test_continue_action_is_available_only_for_continue(status, visible):
    app()
    value = replace(detail(), status=status)
    dialog = InterventionDetailDialog(
        101,
        SimpleNamespace(get_intervention_detail=lambda _id: value),
        continue_service=ContinueServiceStub(),
    )

    dialog.load_detail()

    assert dialog.continue_button.text() == "Tiếp tục bổ trợ"
    assert dialog.continue_button.isHidden() is (not visible)
    assert dialog.continue_button.isEnabled() is visible


def test_continue_confirmation_cancel_does_not_call_service(monkeypatch):
    app()
    service = ContinueServiceStub()
    monkeypatch.setattr(
        "ui.dialogs.intervention_continue_confirmation."
        "QMessageBox.question",
        lambda *_args, **_kwargs: QMessageBox.StandardButton.No,
    )

    assert confirm_continue_support(None, service, 101) is False
    assert service.calls == []


def test_continue_confirmation_accept_calls_exact_contract(monkeypatch):
    app()
    service = ContinueServiceStub()
    monkeypatch.setattr(
        "ui.dialogs.intervention_continue_confirmation."
        "QMessageBox.question",
        lambda *_args, **_kwargs: QMessageBox.StandardButton.Yes,
    )

    assert confirm_continue_support(None, service, 101) is True
    assert service.calls == [101]


def test_cancel_continue_keeps_detail_without_refresh():
    app()
    continuing = replace(detail(), status=InterventionStatus.CONTINUE)

    class Reader:
        def __init__(self):
            self.calls = []

        def get_intervention_detail(self, intervention_id):
            self.calls.append(intervention_id)
            return continuing

    reader = Reader()
    service = ContinueServiceStub()
    dialog = InterventionDetailDialog(
        101,
        reader,
        continue_service=service,
        continue_confirmation=lambda *_args: False,
    )
    dialog.load_detail()

    assert dialog.resume_support() is False
    assert reader.calls == [101]
    assert service.calls == []
    assert dialog.detail.status is InterventionStatus.CONTINUE


def test_successful_continue_refreshes_detail_and_actions():
    app()
    old_reviews = detail().reviews
    continuing = replace(
        detail(old_reviews),
        status=InterventionStatus.CONTINUE,
    )
    in_progress = replace(
        continuing,
        status=InterventionStatus.IN_PROGRESS,
    )

    class Reader:
        def __init__(self):
            self.values = [continuing, in_progress]
            self.calls = []

        def get_intervention_detail(self, intervention_id):
            self.calls.append(intervention_id)
            return self.values.pop(0)

    reader = Reader()
    service = ContinueServiceStub()

    def confirm(_parent, continue_service, intervention_id):
        continue_service.continue_intervention(intervention_id)
        return True

    dialog = InterventionDetailDialog(
        101,
        reader,
        waiting_review_service=SimpleNamespace(),
        continue_service=service,
        continue_confirmation=confirm,
    )
    emitted = []
    dialog.intervention_continued.connect(emitted.append)
    dialog.load_detail()

    assert dialog.resume_support() is True
    assert service.calls == [101]
    assert reader.calls == [101, 101]
    assert dialog.detail.status is InterventionStatus.IN_PROGRESS
    assert dialog.detail.reviews == old_reviews
    assert dialog.status_value_label.text() == "Đang bổ trợ"
    assert dialog.continue_button.isHidden()
    assert not dialog.waiting_review_button.isHidden()
    assert emitted == [101]


def test_continue_failure_is_normalized_and_retryable():
    app()
    continuing = replace(detail(), status=InterventionStatus.CONTINUE)

    class Reader:
        def __init__(self):
            self.calls = []

        def get_intervention_detail(self, intervention_id):
            self.calls.append(intervention_id)
            return continuing

    reader = Reader()
    service = ContinueServiceStub()
    service.fail = True

    def confirm(_parent, continue_service, intervention_id):
        continue_service.continue_intervention(intervention_id)
        return True

    dialog = InterventionDetailDialog(
        101,
        reader,
        continue_service=service,
        continue_confirmation=confirm,
    )
    dialog.load_detail()

    assert dialog.resume_support() is False
    assert reader.calls == [101]
    assert "raw database error" not in dialog.error_label.text()
    assert dialog.continue_button.isEnabled()
    assert dialog.detail.status is InterventionStatus.CONTINUE


class SimpleSignal:
    def __init__(self):
        self.callback = None

    def connect(self, callback):
        self.callback = callback

    def emit(self, value):
        self.callback(value)


class DetailDialogThatContinues:
    kwargs = None

    def __init__(self, **kwargs):
        DetailDialogThatContinues.kwargs = kwargs
        self.intervention_continued = SimpleSignal()

    def load_detail(self):
        return None

    def exec(self):
        self.intervention_continued.emit(731)
        return 0


@pytest.mark.parametrize(
    ("filter_status", "expected_rows"),
    [
        (InterventionStatus.CONTINUE, 0),
        (None, 1),
        (InterventionStatus.IN_PROGRESS, 1),
    ],
)
def test_support_page_refreshes_matching_filter_after_continue(
    filter_status,
    expected_rows,
):
    app()

    class Reader:
        def get_support_cases(self, status=None, **_filters):
            row = replace(report_row(731), status="IN_PROGRESS")
            if status == InterventionStatus.CONTINUE:
                return []
            return [row]

    service = ContinueServiceStub()
    page = SupportPage(
        support_read_service=Reader(),
        intervention_detail_service=SimpleNamespace(),
        intervention_continue_service=service,
        detail_dialog_factory=DetailDialogThatContinues,
    )
    page.school_year_combo.addItem("2026-2027", 2)
    page.school_year_combo.setCurrentIndex(1)
    if filter_status is not None:
        page.status_combo.addItem("filter", filter_status)
        page.status_combo.setCurrentIndex(
            page.status_combo.findData(filter_status)
        )

    assert page.open_intervention_detail(731) is True
    assert DetailDialogThatContinues.kwargs[
        "continue_service"
    ] is service
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
        InterventionStatus.PLANNED,
        InterventionStatus.IN_PROGRESS,
        InterventionStatus.WAITING_REVIEW,
        InterventionStatus.COMPLETED,
    ],
)
def test_continue_service_blocks_every_non_continue_status(status):
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
        service.continue_intervention(101)

    assert repository.update_calls == 0


@pytest.mark.parametrize("invalid_id", [0, -1])
def test_continue_service_validates_id_before_transaction(invalid_id):
    db = FakeDatabase()

    with pytest.raises(ValidationError):
        SupportService(db).continue_intervention(invalid_id)

    assert db.transactions == 0


def test_continue_service_updates_only_status_in_one_transaction():
    continuing = replace(detail(), status=InterventionStatus.CONTINUE)
    in_progress = replace(
        continuing,
        status=InterventionStatus.IN_PROGRESS,
    )

    class Repository:
        def __init__(self):
            self.calls = []

        def get_by_id(self, connection, intervention_id):
            self.calls.append(("get", connection, intervention_id))
            return continuing

        def update_status(self, connection, intervention_id, status):
            self.calls.append(("update", connection, intervention_id, status))
            return in_progress

    db = FakeDatabase()
    repository = Repository()
    result = SupportService(
        db,
        intervention_repository=repository,
    ).continue_intervention(101)

    assert result is in_progress
    assert db.transactions == 1
    assert repository.calls == [
        ("get", db.connection, 101),
        ("update", db.connection, 101, InterventionStatus.IN_PROGRESS),
    ]


def test_real_continue_is_atomic_preserves_history_and_supports_next_review():
    db = get_test_db()
    cleanup_continue_data(db)

    try:
        seeded = seed_report_data(db)
        intervention_id = seeded["completed_intervention_id"]
        repository = InterventionRepository()

        # Arrange a genuine CONTINUE snapshot: retain the first NOT_PASSED
        # review and remove the later PASSED review created by the shared seed.
        with db.transaction() as connection:
            SupportRuleRepository().create(
                connection,
                seeded["subject_id"],
                seeded["school_year_id"],
                Decimal("3.50"),
            )
            reviews = repository.list_reviews(connection, intervention_id)
            passed_review = reviews[-1]
            cursor = connection.cursor()
            cursor.execute(
                "DELETE FROM dbo.INTERVENTION_REVIEWS WHERE review_id = ?",
                passed_review.review_id,
            )
            cursor.execute(
                "DELETE FROM dbo.SCORES WHERE score_id = ?",
                passed_review.score_id,
            )
            repository.update_status(
                connection,
                intervention_id,
                InterventionStatus.CONTINUE,
            )
            before = repository.get_by_id(connection, intervention_id)
            reviews_before = repository.list_reviews(
                connection,
                intervention_id,
            )
            cursor.execute("SELECT COUNT(*) FROM dbo.INTERVENTIONS")
            intervention_count_before = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM dbo.SCORES")
            score_count_before = cursor.fetchone()[0]

        assert [item.result for item in reviews_before] == [
            ReviewResult.NOT_PASSED
        ]

        class FailingRepository(InterventionRepository):
            def update_status(self, *args, **kwargs):
                super().update_status(*args, **kwargs)
                raise RuntimeError("forced failure after update")

        with pytest.raises(RuntimeError):
            SupportService(
                db,
                intervention_repository=FailingRepository(),
            ).continue_intervention(intervention_id)

        with db.transaction() as connection:
            after_failure = repository.get_by_id(
                connection,
                intervention_id,
            )
        assert after_failure.status is InterventionStatus.CONTINUE

        service = SupportService(db)
        continued = service.continue_intervention(intervention_id)
        assert continued.status is InterventionStatus.IN_PROGRESS

        with pytest.raises(InvalidStateTransitionError):
            service.continue_intervention(intervention_id)

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
            cursor.execute(
                """
                SELECT assessment_id
                FROM dbo.ASSESSMENTS
                WHERE assessment_name = ?
                """,
                "TRPT_ASSESSMENT_3",
            )
            review_assessment_id = cursor.fetchone()[0]

        for field in (
            "intervention_id",
            "enrollment_id",
            "subject_id",
            "trigger_score_id",
            "responsible_user_id",
            "start_date",
            "support_method",
            "notes",
            "detected_date",
        ):
            assert getattr(saved, field) == getattr(before, field)
        assert reviews_after == reviews_before
        assert intervention_count_after == intervention_count_before
        assert score_count_after == score_count_before

        report = ReportService(db)
        continue_rows = report.get_support_cases(
            seeded["school_year_id"],
            status=InterventionStatus.CONTINUE,
        )
        all_rows = report.get_support_cases(seeded["school_year_id"])
        in_progress_rows = report.get_support_cases(
            seeded["school_year_id"],
            status=InterventionStatus.IN_PROGRESS,
        )
        assert all(row.intervention_id != intervention_id for row in continue_rows)
        assert next(
            row for row in all_rows if row.intervention_id == intervention_id
        ).status == "IN_PROGRESS"
        assert any(row.intervention_id == intervention_id for row in in_progress_rows)

        service.mark_waiting_review(intervention_id)
        review_score = ScoreService(db).create_score(
            saved.enrollment_id,
            review_assessment_id,
            "4.20",
        )
        completed = service.review_intervention(
            intervention_id,
            review_score.score_id,
            date(2026, 11, 20),
            "Đã đạt ngưỡng sau khi tiếp tục.",
        )
        assert completed.status is InterventionStatus.COMPLETED

        detail_after = service.get_intervention_detail(intervention_id)
        assert [item.result for item in detail_after.reviews] == [
            ReviewResult.NOT_PASSED,
            ReviewResult.PASSED,
        ]
        assert [item.intervention_id for item in detail_after.reviews] == [
            intervention_id,
            intervention_id,
        ]
        with pytest.raises(InvalidStateTransitionError):
            service.continue_intervention(intervention_id)
    finally:
        cleanup_continue_data(db)


def test_continue_ui_has_no_sql_or_direct_repository_access():
    modules = (
        inspect.getmodule(InterventionDetailDialog),
        inspect.getmodule(confirm_continue_support),
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
    ):
        assert forbidden not in upper_source
