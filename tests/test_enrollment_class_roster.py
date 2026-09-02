from contextlib import contextmanager

import pytest

from exceptions import ValidationError
from models.enums import EnrollmentStatus
from repositories.enrollment_repository import EnrollmentRepository
from services.enrollment_service import EnrollmentService


class DbStub:
    def __init__(self):
        self.connection = object()
        self.transactions = 0

    @contextmanager
    def transaction(self):
        self.transactions += 1
        yield self.connection


class EnrollmentRepositoryStub:
    def __init__(self, result=()):
        self.result = list(result)
        self.calls = []

    def list_by_class(
        self,
        connection,
        class_id,
        school_year_id,
        status,
    ):
        self.calls.append(
            (connection, class_id, school_year_id, status)
        )
        return self.result


def test_list_class_enrollments_uses_active_roster_in_one_transaction():
    db = DbStub()
    repository = EnrollmentRepositoryStub(result=["student-row"])
    service = EnrollmentService(
        db,
        enrollment_repository=repository,
    )

    result = service.list_class_enrollments(61, 2)

    assert result == ["student-row"]
    assert repository.calls == [
        (db.connection, 61, 2, EnrollmentStatus.ACTIVE)
    ]
    assert db.transactions == 1


@pytest.mark.parametrize("class_id,school_year_id", [(0, 2), (61, 0)])
def test_list_class_enrollments_validates_context_ids(
    class_id,
    school_year_id,
):
    db = DbStub()
    service = EnrollmentService(
        db,
        enrollment_repository=EnrollmentRepositoryStub(),
    )

    with pytest.raises(ValidationError):
        service.list_class_enrollments(class_id, school_year_id)

    assert db.transactions == 0


class Row:
    enrollment_id = 700
    student_id = "student-1"
    student_code = "HS01"
    full_name = "Học sinh 1"
    class_id = 61
    class_name = "6A1"
    grade_number = 6
    school_year_id = 2
    school_year_name = "2026-2027"
    status = "ACTIVE"


class Cursor:
    def __init__(self):
        self.sql = ""
        self.parameters = ()

    def execute(self, sql, *parameters):
        self.sql = sql
        self.parameters = parameters
        return self

    def fetchall(self):
        return [Row()]


class Connection:
    def __init__(self):
        self.cursor_value = Cursor()
        self.commit_calls = 0

    def cursor(self):
        return self.cursor_value

    def commit(self):
        self.commit_calls += 1


def test_class_roster_repository_is_parameterized_and_does_not_commit():
    connection = Connection()

    rows = EnrollmentRepository().list_by_class(
        connection,
        61,
        2,
        EnrollmentStatus.ACTIVE,
    )

    sql = connection.cursor_value.sql.upper()
    assert "SELECT *" not in sql
    assert connection.cursor_value.parameters == (61, 2, "ACTIVE")
    assert rows[0].enrollment_id == 700
    assert connection.commit_calls == 0
