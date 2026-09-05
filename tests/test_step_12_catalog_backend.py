from contextlib import contextmanager
from datetime import date
import inspect

import pytest

from exceptions import BusinessRuleError, DuplicateError, ValidationError
from models.dto import Grade, SchoolClass, SchoolYear
from repositories.academic_repository import AcademicRepository
from services.academic_service import AcademicService


class FakeDatabase:
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


class FakeRepository:
    def __init__(self):
        self.years = {
            1: (1, "2025-2026", date(2025, 9, 1), date(2026, 5, 31), False),
            2: (2, "2026-2027", date(2026, 9, 1), date(2027, 5, 31), True),
        }
        self.grades = {
            6: (6, 6, "Khối 6"),
            7: (7, 7, "Khối 7"),
        }
        self.classes = {
            61: (61, "6A1", 6, 6, 2, "2026-2027", "GV A", "ACTIVE"),
        }
        self.class_has_history = False
        self.calls = []
        self.fail_update = False

    def list_school_years(self, connection):
        return list(self.years.values())

    def list_grades(self, connection):
        return list(self.grades.values())

    def get_grade_by_number(self, connection, number):
        return next((item for item in self.grades.values() if item[1] == number), None)

    def get_grade_by_id(self, connection, grade_id):
        return self.grades.get(grade_id)

    def create_grade(self, connection, number, name):
        self.calls.append(("create_grade", number, name))
        self.grades[number] = (number, number, name)
        return number

    def update_grade_name(self, connection, grade_id, name):
        self.calls.append(("update_grade", grade_id, name))

    def get_school_year_by_name(self, connection, name):
        return next((item for item in self.years.values() if item[1] == name), None)

    def get_school_year_by_id(self, connection, year_id):
        return self.years.get(year_id)

    def clear_current_school_years(self, connection):
        self.calls.append(("clear_current",))

    def create_school_year(self, connection, name, start, end, current):
        self.calls.append(("create_year", name, start, end, current))
        return 3

    def update_school_year(self, connection, year_id, name, start, end, current):
        self.calls.append(("update_year", year_id, name, start, end, current))

    def get_class_by_name_and_year(self, connection, name, year_id):
        for item in self.classes.values():
            if item[1] == name and item[4] == year_id:
                return item[0]
        return None

    def create_class(self, connection, name, grade_id, year_id, teacher, status="ACTIVE"):
        self.calls.append(("create_class", name, grade_id, year_id, teacher, status))
        return 99

    def get_class_by_id(self, connection, class_id):
        return self.classes.get(class_id)

    def list_classes_by_school_year(self, connection, year_id):
        return []

    def list_catalog_classes(self, connection, year_id, grade_id=None):
        self.calls.append(("list_classes", year_id, grade_id))
        return []

    def class_has_enrollments(self, connection, class_id):
        return self.class_has_history

    def update_class(self, connection, class_id, name, grade_id, year_id, teacher, status):
        if self.fail_update:
            raise RuntimeError("repository failure")
        self.calls.append(
            ("update_class", class_id, name, grade_id, year_id, teacher, status)
        )


def build():
    db = FakeDatabase()
    repo = FakeRepository()
    return AcademicService(db, repo), db, repo


def test_catalog_dtos_are_explicit_and_class_active_is_derived():
    school_year = SchoolYear(1, "2026-2027", None, None, True)
    grade = Grade(6, 6, "Khối 6")
    school_class = SchoolClass(1, "6A1", 6, 6, 1, "2026-2027", None, "ACTIVE")

    assert school_year.is_current is True
    assert grade.grade_number == 6
    assert school_class.is_active is True
    assert SchoolClass(1, "6A1", 6, 6, 1, "Y", None, "INACTIVE").is_active is False


def test_catalog_reads_return_dtos_and_service_owns_transactions():
    service, db, _ = build()

    years = service.list_catalog_school_years()
    grades = service.list_catalog_grades()
    classes = service.list_catalog_classes(2, 6)

    assert isinstance(years[0], SchoolYear)
    assert isinstance(grades[0], Grade)
    assert classes == []
    assert db.transactions == 3


def test_create_current_school_year_trims_and_clears_previous_current():
    service, db, repo = build()

    result = service.create_school_year(
        "  2027-2028  ",
        date(2027, 9, 1),
        date(2028, 5, 31),
        True,
    )

    assert result == 3
    assert repo.calls == [
        ("clear_current",),
        ("create_year", "2027-2028", date(2027, 9, 1), date(2028, 5, 31), True),
    ]
    assert db.commits == 1


def test_duplicate_school_year_is_blocked_before_insert():
    service, db, repo = build()

    with pytest.raises(DuplicateError):
        service.create_school_year(
            "2026-2027",
            date(2026, 9, 1),
            date(2027, 5, 31),
        )

    assert not any(call[0] == "create_year" for call in repo.calls)
    assert db.rollbacks == 1


def test_update_school_year_preserves_id_and_can_make_it_current():
    service, _, repo = build()

    service.update_school_year(
        1,
        "2025-2026 revised",
        date(2025, 8, 15),
        date(2026, 6, 1),
        True,
    )

    assert repo.calls[-2:] == [
        ("clear_current",),
        (
            "update_year",
            1,
            "2025-2026 revised",
            date(2025, 8, 15),
            date(2026, 6, 1),
            True,
        ),
    ]


@pytest.mark.parametrize(
    "args",
    [
        ("", date(2026, 9, 1), date(2027, 5, 31), False),
        ("Y", None, date(2027, 5, 31), False),
        ("Y", date(2027, 5, 31), date(2026, 9, 1), False),
        ("Y", date(2026, 9, 1), date(2027, 5, 31), "yes"),
        ("X" * 21, date(2026, 9, 1), date(2027, 5, 31), False),
    ],
)
def test_invalid_school_year_data_is_blocked_before_transaction(args):
    service, db, _ = build()

    with pytest.raises(ValidationError):
        service.create_school_year(*args)

    assert db.transactions == 0


def test_create_grade_uses_database_number_and_trims_optional_name():
    service, _, repo = build()

    result = service.create_grade(8, "  Khối Tám  ")

    assert result == 8
    assert repo.calls[-1] == ("create_grade", 8, "Khối Tám")


def test_duplicate_grade_is_blocked():
    service, _, _ = build()

    with pytest.raises(DuplicateError):
        service.create_grade(6, "Khối 6 khác")


@pytest.mark.parametrize("number", [5, 13, True, "6"])
def test_grade_number_must_match_real_schema_range(number):
    service, db, _ = build()

    with pytest.raises(ValidationError):
        service.create_grade(number)

    assert db.transactions == 0


def test_grade_edit_changes_name_only_and_keeps_identity_number():
    service, _, repo = build()

    service.update_grade_name(6, "  Khối Sáu  ")

    assert repo.calls[-1] == ("update_grade", 6, "Khối Sáu")


def test_create_class_validates_parents_and_uses_ids_not_labels():
    service, _, repo = build()

    class_id = service.create_class(
        "  7A2  ",
        grade_id=7,
        school_year_id=2,
        homeroom_teacher="  GV B  ",
        status="INACTIVE",
    )

    assert class_id == 99
    assert repo.calls[-1] == (
        "create_class", "7A2", 7, 2, "GV B", "INACTIVE"
    )


@pytest.mark.parametrize(
    ("grade_id", "year_id"),
    [(999, 2), (6, 999)],
)
def test_create_class_blocks_missing_foreign_key(grade_id, year_id):
    service, _, repo = build()

    with pytest.raises(ValidationError):
        service.create_class("6A2", grade_id, year_id)

    assert not any(call[0] == "create_class" for call in repo.calls)


def test_duplicate_class_is_scoped_to_school_year():
    service, _, _ = build()

    with pytest.raises(DuplicateError):
        service.create_class("6A1", 6, 2)


def test_referenced_class_cannot_change_grade_or_school_year():
    service, _, repo = build()
    repo.class_has_history = True

    with pytest.raises(BusinessRuleError):
        service.update_class(61, "6A1", 7, 2, "GV A", "ACTIVE")

    assert not any(call[0] == "update_class" for call in repo.calls)


def test_referenced_class_can_update_name_teacher_and_status_without_deletion():
    service, _, repo = build()
    repo.class_has_history = True

    service.update_class(61, "6A1 mới", 6, 2, "GV mới", "INACTIVE")

    assert repo.calls[-1] == (
        "update_class", 61, "6A1 mới", 6, 2, "GV mới", "INACTIVE"
    )


def test_toggle_class_is_one_service_transaction_and_never_deletes():
    service, db, repo = build()

    service.set_class_active(61, False)

    assert db.transactions == 1
    assert repo.calls[-1][-1] == "INACTIVE"
    assert not any(call[0].startswith("delete") for call in repo.calls)


def test_repository_failure_rolls_back_service_transaction():
    service, db, repo = build()
    repo.fail_update = True

    with pytest.raises(RuntimeError):
        service.set_class_active(61, False)

    assert db.rollbacks == 1
    assert db.commits == 0


def test_repository_has_no_commit_and_catalog_queries_are_parameterized():
    source = inspect.getsource(AcademicRepository).upper()

    assert ".COMMIT(" not in source
    assert "SELECT *" not in source
    assert "WHERE C.SCHOOL_YEAR_ID = ?" in source
    assert "AND C.GRADE_ID = ?" in source


def test_academic_service_has_no_delete_catalog_api():
    source = inspect.getsource(AcademicService).upper()

    assert "DELETE_SCHOOL_YEAR" not in source
    assert "DELETE_GRADE" not in source
    assert "DELETE_CLASS" not in source
