import inspect
import os
from contextlib import contextmanager
from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from exceptions import BusinessRuleError, ValidationError
from models.dto.assessment import Assessment
from models.dto.score import Score, ScoreRosterItem
from models.enums import AssessmentStatus
from repositories.intervention_repository import InterventionRepository
from services.score_service import ScoreService
from ui.pages.scores_page import ScoresPage


NOW = datetime(2026, 9, 2)


def stored_score(value=Decimal("6.50")):
    return Score(91, 71, 101, value, NOW, NOW)


class DbStub:
    def __init__(self):
        self.connection = object()
        self.transactions = 0
        self.commits = 0
        self.rollbacks = 0

    @contextmanager
    def transaction(self):
        self.transactions += 1
        try:
            yield self.connection
        except Exception:
            self.rollbacks += 1
            raise
        else:
            self.commits += 1


class ScoreRepositoryStub:
    def __init__(self, score=None, fail=False):
        self.score = stored_score() if score is None else score
        self.fail = fail
        self.update_calls = []

    def get_by_id(self, _connection, score_id):
        return self.score if self.score and self.score.score_id == score_id else None

    def update(self, _connection, score_id, score_value):
        self.update_calls.append((score_id, score_value))
        if self.fail:
            raise RuntimeError("update failed")
        self.score = replace(self.score, score=score_value)
        return self.score


class LinkRepositoryStub:
    def __init__(self, linked=False):
        self.linked = linked
        self.calls = []

    def is_score_linked_to_support(self, connection, score_id):
        self.calls.append((connection, score_id))
        return self.linked


def make_service(*, score=None, linked=False, fail=False):
    db = DbStub()
    scores = ScoreRepositoryStub(score, fail)
    links = LinkRepositoryStub(linked)
    service = ScoreService(
        db,
        score_repository=scores,
        intervention_repository=links,
    )
    return service, db, scores, links


def test_unlinked_score_update_preserves_identity_and_context():
    service, db, repository, links = make_service()

    updated = service.update_score(91, Decimal("7.25"))

    assert updated.score_id == 91
    assert updated.enrollment_id == 71
    assert updated.assessment_id == 101
    assert updated.score == Decimal("7.25")
    assert repository.update_calls == [(91, Decimal("7.25"))]
    assert links.calls == [(db.connection, 91)]
    assert db.commits == 1


def test_linked_score_is_blocked_in_same_transaction_without_update():
    service, db, repository, _links = make_service(linked=True)

    with pytest.raises(BusinessRuleError, match="lịch sử bổ trợ"):
        service.update_score(91, Decimal("7.25"))

    assert repository.score.score == Decimal("6.50")
    assert repository.update_calls == []
    assert db.rollbacks == 1
    assert db.commits == 0


def test_missing_score_is_rejected_before_link_check():
    service, db, repository, links = make_service(score=False)

    with pytest.raises(ValidationError, match="Không tìm thấy"):
        service.update_score(91, Decimal("7"))

    assert links.calls == []
    assert repository.update_calls == []
    assert db.rollbacks == 1


def test_repository_failure_rolls_back_update_transaction():
    service, db, repository, _links = make_service(fail=True)

    with pytest.raises(RuntimeError, match="update failed"):
        service.update_score(91, Decimal("7"))

    assert repository.score.score == Decimal("6.50")
    assert db.rollbacks == 1
    assert db.commits == 0


@pytest.mark.parametrize(
    "value",
    [
        Decimal("-0.01"),
        Decimal("10.01"),
        Decimal("NaN"),
        Decimal("Infinity"),
        True,
        None,
        "bad",
        Decimal("1.234"),
    ],
)
def test_update_reuses_create_score_validation(value):
    service, db, repository, _links = make_service()

    with pytest.raises(ValidationError):
        service.update_score(91, value)

    assert db.transactions == 0
    assert repository.update_calls == []


def test_repository_link_check_is_parameterized_read_only():
    class Cursor:
        def __init__(self):
            self.call = None

        def execute(self, sql, *parameters):
            self.call = (sql, parameters)

        def fetchone(self):
            return (1,)

    class Connection:
        def __init__(self):
            self.cursor_value = Cursor()
            self.commits = 0

        def cursor(self):
            return self.cursor_value

        def commit(self):
            self.commits += 1

    connection = Connection()

    assert InterventionRepository().is_score_linked_to_support(
        connection, 91
    ) is True
    sql, parameters = connection.cursor_value.call
    assert "INTERVENTIONS" in sql
    assert "INTERVENTION_REVIEWS" in sql
    assert parameters == (91, 91)
    assert connection.commits == 0


class AcademicUiStub:
    def list_school_years(self):
        return [(2, "2026-2027", None, None, True)]

    def list_grades(self):
        return [(6, 6, "Khối 6")]

    def list_classes_by_school_year(self, _school_year_id):
        return [(61, "6A1", 6, None, True)]

    def list_active_subjects(self):
        return [(11, "M1", "Môn 1")]

    def list_assessments(self, school_year_id, subject_id=None):
        return [Assessment(101, subject_id, school_year_id, "Giữa kỳ", 1,
                           "MIDTERM", date(2026, 10, 1),
                           AssessmentStatus.ACTIVE, NOW)]


class ScoreUiStub:
    def __init__(self, *, editable=True, update_error=None):
        self.editable = editable
        self.update_error = update_error
        self.value = Decimal("6.50")
        self.update_calls = []

    def list_score_roster(self, *_context):
        return [ScoreRosterItem(71, "s1", "HS1", "Học sinh 1", 101,
                                91, self.value)]

    def can_edit_score(self, score_id):
        assert score_id == 91
        return self.editable

    def update_score(self, score_id, value):
        self.update_calls.append((score_id, value))
        if self.update_error:
            raise self.update_error
        self.value = value
        return stored_score(value)


def complete_context(page):
    page.initialize_scores()
    page.grade_combo.setCurrentIndex(page.grade_combo.findData(6))
    page.class_combo.setCurrentIndex(page.class_combo.findData(61))
    page.subject_combo.setCurrentIndex(page.subject_combo.findData(11))
    page.assessment_combo.setCurrentIndex(
        page.assessment_combo.findData(101)
    )
    page.score_table.selectRow(0)


def make_page(service):
    QApplication.instance() or QApplication([])
    page = ScoresPage(AcademicUiStub(), score_service=service)
    complete_context(page)
    return page


def test_ui_edit_save_refreshes_value_and_keeps_score_id():
    service = ScoreUiStub()
    page = make_page(service)

    assert page.begin_edit_selected_score() is True
    assert bool(page.score_table.item(0, 3).flags() & Qt.ItemFlag.ItemIsEditable)
    page.score_table.item(0, 3).setText("7,25")
    assert page.save_score_edit() is True

    assert service.update_calls == [(91, Decimal("7.25"))]
    assert page.score_table.item(0, 3).text() == "7.25"
    assert page.score_id_at_row(0) == 91
    assert not bool(page.score_table.item(0, 3).flags() & Qt.ItemFlag.ItemIsEditable)


def test_ui_cancel_restores_value_without_service_update():
    service = ScoreUiStub()
    page = make_page(service)
    page.begin_edit_selected_score()
    page.score_table.item(0, 3).setText("9")

    assert page.cancel_score_edit() is True
    assert page.score_table.item(0, 3).text() == "6.50"
    assert service.update_calls == []


def test_ui_blocks_linked_score_before_edit_mode():
    service = ScoreUiStub(editable=False)
    page = make_page(service)

    assert page.begin_edit_selected_score() is False
    assert "lịch sử bổ trợ" in page.context_status_label.text()
    assert not bool(page.score_table.item(0, 3).flags() & Qt.ItemFlag.ItemIsEditable)


def test_ui_does_not_offer_edit_for_missing_score():
    service = ScoreUiStub()
    page = make_page(service)
    page.set_score_rows([
        ScoreRosterItem(71, "s1", "HS1", "Học sinh 1", 101, None, None)
    ])
    page.score_table.selectRow(0)

    assert page.edit_button.isEnabled() is False
    assert page.begin_edit_selected_score() is False
    assert service.update_calls == []


def test_ui_update_failure_keeps_page_in_edit_mode_and_usable():
    service = ScoreUiStub(update_error=BusinessRuleError("locked"))
    page = make_page(service)
    page.begin_edit_selected_score()
    page.score_table.item(0, 3).setText("8")

    assert page.save_score_edit() is False
    assert page.context_status_label.text() == "locked"
    assert page.cancel_edit_button.isEnabled() is True
    assert page.cancel_score_edit() is True


def test_update_path_does_not_call_support_service():
    source = inspect.getsource(ScoreService.update_score).upper()
    assert "SUPPORTSERVICE" not in source
    assert "CREATE_SCORE_AND_DETECT" not in source
