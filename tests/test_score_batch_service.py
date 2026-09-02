from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal

import pytest

from exceptions import DuplicateError, ValidationError
from models.dto.score import Score, ScoreCreateData
from services.score_service import ScoreService


class TransactionDb:
    def __init__(self):
        self.connection = object()
        self.transactions = 0
        self.rollbacks = 0
        self.commits = 0
        self.pending = []
        self.stored = []

    @contextmanager
    def transaction(self):
        self.transactions += 1
        try:
            yield self.connection
        except Exception:
            self.pending.clear()
            self.rollbacks += 1
            raise
        else:
            self.stored.extend(self.pending)
            self.pending.clear()
            self.commits += 1


class ExistingRepository:
    def __init__(self, ids):
        self.ids = set(ids)

    def get_by_id(self, _connection, item_id):
        return object() if item_id in self.ids else None

    def get_assessment_by_id(self, connection, item_id):
        return self.get_by_id(connection, item_id)


class ScoreRepositoryStub:
    def __init__(self, db, existing=()):
        self.db = db
        self.existing = set(existing)

    def get_by_enrollment_assessment(
        self,
        _connection,
        enrollment_id,
        assessment_id,
    ):
        key = (enrollment_id, assessment_id)
        pending_keys = {
            (score.enrollment_id, score.assessment_id)
            for score in self.db.pending
        }
        return object() if key in self.existing | pending_keys else None

    def create(
        self,
        _connection,
        enrollment_id,
        assessment_id,
        score_value,
    ):
        now = datetime(2026, 9, 2)
        score = Score(
            score_id=len(self.db.pending) + 1,
            enrollment_id=enrollment_id,
            assessment_id=assessment_id,
            score=score_value,
            created_at=now,
            updated_at=now,
        )
        self.db.pending.append(score)
        return score


def make_service(existing=()):
    db = TransactionDb()
    service = ScoreService(
        db,
        score_repository=ScoreRepositoryStub(db, existing),
        enrollment_repository=ExistingRepository({10, 20}),
        academic_repository=ExistingRepository({100}),
    )
    return service, db


def entries():
    return (
        ScoreCreateData(10, 100, Decimal("7.25")),
        ScoreCreateData(20, 100, Decimal("8.50")),
    )


def test_create_scores_saves_multiple_scores_in_one_transaction():
    service, db = make_service()

    created = service.create_scores(entries())

    assert [item.score for item in created] == [
        Decimal("7.25"),
        Decimal("8.50"),
    ]
    assert db.transactions == 1
    assert db.commits == 1
    assert db.rollbacks == 0
    assert len(db.stored) == 2


def test_create_scores_rolls_back_entire_batch_on_duplicate():
    service, db = make_service(existing={(20, 100)})

    with pytest.raises(DuplicateError):
        service.create_scores(entries())

    assert db.transactions == 1
    assert db.commits == 0
    assert db.rollbacks == 1
    assert db.stored == []


def test_create_scores_does_not_call_support_dependencies():
    class ForbiddenDependency:
        def __getattr__(self, name):
            raise AssertionError(f"Unexpected support call: {name}")

    service, db = make_service()
    forbidden = ForbiddenDependency()
    service.rule_repository = forbidden
    service.intervention_repository = forbidden

    service.create_scores(entries())

    assert len(db.stored) == 2


@pytest.mark.parametrize(
    "batch",
    [
        (),
        (ScoreCreateData(0, 100, Decimal("5")),),
        (ScoreCreateData(10, 0, Decimal("5")),),
        (ScoreCreateData(10, 100, Decimal("10.01")),),
    ],
)
def test_create_scores_validates_batch_before_transaction(batch):
    service, db = make_service()

    with pytest.raises(ValidationError):
        service.create_scores(batch)

    assert db.transactions == 0
