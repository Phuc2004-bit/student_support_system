from contextlib import contextmanager
from datetime import datetime
from decimal import Decimal

import pyodbc
import pytest

from exceptions import DuplicateError, ValidationError
from models.dto.score import Score, ScoreCreateData
from services.score_service import ScoreService


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


class LookupRepository:
    def get_by_id(self, _connection, _item_id):
        return object()

    def get_assessment_by_id(self, _connection, _item_id):
        return object()


class ScoreRepositoryStub:
    def __init__(self, *, existing=(), fail_on_create=None):
        self.existing = set(existing)
        self.fail_on_create = fail_on_create
        self.created = []

    def get_by_enrollment_assessment(
        self,
        _connection,
        enrollment_id,
        assessment_id,
    ):
        key = (enrollment_id, assessment_id)
        return object() if key in self.existing else None

    def create(
        self,
        _connection,
        enrollment_id,
        assessment_id,
        score_value,
    ):
        if self.fail_on_create == len(self.created) + 1:
            raise RuntimeError("repository failure")
        now = datetime(2026, 9, 2)
        result = Score(
            score_id=len(self.created) + 1,
            enrollment_id=enrollment_id,
            assessment_id=assessment_id,
            score=score_value,
            created_at=now,
            updated_at=now,
        )
        self.created.append(result)
        return result


def make_service(score_repository=None):
    db = DbStub()
    repository = score_repository or ScoreRepositoryStub()
    service = ScoreService(
        db,
        score_repository=repository,
        enrollment_repository=LookupRepository(),
        academic_repository=LookupRepository(),
    )
    return service, db, repository


@pytest.mark.parametrize(
    "value,expected",
    [
        (0, Decimal("0")),
        (10, Decimal("10")),
        (7, Decimal("7")),
        (7.25, Decimal("7.25")),
        ("8.50", Decimal("8.50")),
        (Decimal("9.99"), Decimal("9.99")),
    ],
)
def test_valid_numeric_scores_are_normalized_to_decimal(value, expected):
    service, db, repository = make_service()

    created = service.create_score(10, 100, value)

    assert created.score == expected
    assert isinstance(repository.created[0].score, Decimal)
    assert db.commits == 1


@pytest.mark.parametrize(
    "value",
    [
        Decimal("-0.01"),
        Decimal("10.01"),
        "not-a-number",
        "",
        "   ",
        True,
        Decimal("NaN"),
        Decimal("Infinity"),
        Decimal("-Infinity"),
        Decimal("1.234"),
        Decimal("1E-999999"),
        object(),
    ],
)
def test_invalid_scores_are_rejected_before_transaction(value):
    service, db, repository = make_service()

    with pytest.raises(ValidationError):
        service.create_score(10, 100, value)

    assert db.transactions == 0
    assert repository.created == []


@pytest.mark.parametrize(
    "enrollment_id,assessment_id",
    [
        (0, 100),
        (-1, 100),
        (True, 100),
        (None, 100),
        ("10", 100),
        (10, 0),
        (10, -1),
        (10, False),
        (10, None),
        (10, "100"),
    ],
)
def test_invalid_required_identifiers_are_rejected_before_transaction(
    enrollment_id,
    assessment_id,
):
    service, db, repository = make_service()

    with pytest.raises(ValidationError):
        service.create_scores(
            (
                ScoreCreateData(
                    enrollment_id,
                    assessment_id,
                    Decimal("5"),
                ),
            )
        )

    assert db.transactions == 0
    assert repository.created == []


def test_duplicate_keys_inside_batch_are_rejected_before_transaction():
    service, db, repository = make_service()
    batch = (
        ScoreCreateData(10, 100, Decimal("5")),
        ScoreCreateData(10, 100, Decimal("6")),
    )

    with pytest.raises(DuplicateError):
        service.create_scores(batch)

    assert db.transactions == 0
    assert repository.created == []


def test_invalid_item_prevents_other_valid_batch_item_from_being_inserted():
    service, db, repository = make_service()
    batch = (
        ScoreCreateData(10, 100, Decimal("5")),
        ScoreCreateData(20, 100, Decimal("NaN")),
    )

    with pytest.raises(ValidationError):
        service.create_scores(batch)

    assert db.transactions == 0
    assert repository.created == []


def test_repository_failure_in_middle_of_batch_rolls_back_transaction():
    repository = ScoreRepositoryStub(fail_on_create=2)
    service, db, _repository = make_service(repository)
    batch = (
        ScoreCreateData(10, 100, Decimal("5")),
        ScoreCreateData(20, 100, Decimal("6")),
    )

    with pytest.raises(RuntimeError, match="repository failure"):
        service.create_scores(batch)

    assert db.commits == 0
    assert db.rollbacks == 1


class RaceDuplicateRepository(ScoreRepositoryStub):
    def create(self, *_args):
        raise pyodbc.IntegrityError(
            "23000",
            "Violation of UNIQUE KEY constraint (2627)",
        )


def test_database_unique_race_is_normalized_to_duplicate_error():
    service, db, _repository = make_service(
        RaceDuplicateRepository()
    )

    with pytest.raises(DuplicateError):
        service.create_score(10, 100, Decimal("5"))

    assert db.commits == 0
    assert db.rollbacks == 1


def test_existing_database_duplicate_is_rejected_without_create():
    repository = ScoreRepositoryStub(existing={(10, 100)})
    service, db, _repository = make_service(repository)

    with pytest.raises(DuplicateError):
        service.create_score(10, 100, Decimal("5"))

    assert repository.created == []
    assert db.rollbacks == 1
