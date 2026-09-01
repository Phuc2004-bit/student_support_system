from contextlib import contextmanager
from datetime import date, datetime
from types import SimpleNamespace

import pytest

from exceptions import ValidationError
from models.dto import Assessment
from models.enums import AssessmentStatus
from repositories.academic_repository import AcademicRepository
from services.academic_service import AcademicService
from services.assessment_contract import AssessmentReadServiceContract


def assessment(
    assessment_id: int = 1,
    subject_id: int = 2,
    school_year_id: int = 3,
) -> Assessment:
    return Assessment(
        assessment_id=assessment_id,
        subject_id=subject_id,
        school_year_id=school_year_id,
        assessment_name="Giữa kỳ",
        semester=1,
        assessment_type="MIDTERM",
        assessment_date=date(2026, 10, 15),
        status=AssessmentStatus.ACTIVE,
        created_at=datetime(2026, 9, 1),
    )


class Database:
    def __init__(self):
        self.connection = object()
        self.transactions = 0

    @contextmanager
    def transaction(self):
        self.transactions += 1
        yield self.connection


class Repository:
    def __init__(self):
        self.get_args = None
        self.list_args = None

    def get_assessment_by_id(self, connection, assessment_id):
        self.get_args = (connection, assessment_id)
        return assessment(assessment_id=assessment_id)

    def list_assessments(
        self,
        connection,
        school_year_id,
        subject_id,
        semester,
        status,
    ):
        self.list_args = (
            connection,
            school_year_id,
            subject_id,
            semester,
            status,
        )
        return [assessment(subject_id=subject_id or 2)]


def test_assessment_read_contract_declares_existing_service_api():
    assert AssessmentReadServiceContract is not None
    assert hasattr(AcademicService, "get_assessment")
    assert hasattr(AcademicService, "list_assessments")


def test_get_assessment_by_id_uses_repository_transaction():
    database = Database()
    repository = Repository()
    service = AcademicService(database, repository)

    result = service.get_assessment(7)

    assert result.assessment_id == 7
    assert database.transactions == 1
    assert repository.get_args == (database.connection, 7)


def test_list_assessments_supports_read_context_filters():
    database = Database()
    repository = Repository()
    service = AcademicService(database, repository)

    result = service.list_assessments(
        school_year_id=3,
        subject_id=2,
        semester=1,
        status=AssessmentStatus.ACTIVE,
    )

    assert result[0].subject_id == 2
    assert database.transactions == 1
    assert repository.list_args == (
        database.connection,
        3,
        2,
        1,
        AssessmentStatus.ACTIVE,
    )


@pytest.mark.parametrize(
    ("kwargs", "message"),
    (
        ({"school_year_id": 0}, "school_year_id"),
        ({"school_year_id": True}, "school_year_id"),
        ({"school_year_id": "3"}, "school_year_id"),
        ({"school_year_id": 3, "subject_id": -1}, "subject_id"),
        ({"school_year_id": 3, "subject_id": False}, "subject_id"),
        ({"school_year_id": 3, "semester": 3}, "semester"),
        ({"school_year_id": 3, "semester": True}, "semester"),
        ({"school_year_id": 3, "status": "ACTIVE"}, "status"),
    ),
)
def test_invalid_assessment_filters_are_rejected(kwargs, message):
    service = AcademicService(Database(), Repository())

    with pytest.raises(ValidationError, match=message):
        service.list_assessments(**kwargs)


@pytest.mark.parametrize("assessment_id", (0, -1, True, "1"))
def test_invalid_assessment_id_is_rejected(assessment_id):
    service = AcademicService(Database(), Repository())

    with pytest.raises(ValidationError, match="assessment_id"):
        service.get_assessment(assessment_id)


class Cursor:
    def __init__(self):
        self.sql = None
        self.parameters = None

    def execute(self, sql, *parameters):
        self.sql = sql
        self.parameters = parameters

    def fetchall(self):
        return [SimpleNamespace(
            assessment_id=11,
            subject_id=2,
            school_year_id=3,
            assessment_name="Cuối kỳ",
            semester=2,
            assessment_type="FINAL",
            assessment_date=date(2027, 5, 10),
            status="LOCKED",
            created_at=datetime(2026, 9, 1),
        )]


class Connection:
    def __init__(self):
        self.cursor_instance = Cursor()
        self.commit_calls = 0

    def cursor(self):
        return self.cursor_instance

    def commit(self):
        self.commit_calls += 1


def test_repository_query_is_parameterized_maps_dto_and_does_not_commit():
    connection = Connection()
    repository = AcademicRepository()

    result = repository.list_assessments(
        connection,
        school_year_id=3,
        subject_id=2,
        semester=2,
        status=AssessmentStatus.LOCKED,
    )

    assert result == [Assessment(
        assessment_id=11,
        subject_id=2,
        school_year_id=3,
        assessment_name="Cuối kỳ",
        semester=2,
        assessment_type="FINAL",
        assessment_date=date(2027, 5, 10),
        status=AssessmentStatus.LOCKED,
        created_at=datetime(2026, 9, 1),
    )]
    assert "SELECT *" not in connection.cursor_instance.sql.upper()
    assert connection.cursor_instance.parameters == (3, 2, 2, "LOCKED")
    assert connection.commit_calls == 0
