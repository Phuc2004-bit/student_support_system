from contextlib import contextmanager

from services.academic_service import AcademicService


class FakeDatabase:
    def __init__(self):
        self.connection = object()
        self.transaction_count = 0

    @contextmanager
    def transaction(self):
        self.transaction_count += 1
        yield self.connection


class FakeRepository:
    def list_school_years(self, connection):
        return [(2, "2026-2027", None, None, True)]

    def list_grades(self, connection):
        return [(6, 6, "Khối 6")]


def test_list_school_years_uses_repository_transaction():
    db = FakeDatabase()
    service = AcademicService(db, FakeRepository())

    result = service.list_school_years()

    assert result[0][0] == 2
    assert db.transaction_count == 1


def test_list_grades_uses_repository_transaction():
    db = FakeDatabase()
    service = AcademicService(db, FakeRepository())

    result = service.list_grades()

    assert result == [(6, 6, "Khối 6")]
    assert db.transaction_count == 1
