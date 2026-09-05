from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
import inspect

import pyodbc
import pytest

from exceptions import BusinessRuleError, DatabaseError, DuplicateError, ValidationError
from models.dto import Assessment, Subject, SupportRule
from models.enums import AssessmentStatus
from repositories import AcademicRepository, SupportRuleRepository
from services import AcademicService


NOW = datetime(2026, 1, 1)


class FakeDatabase:
    def __init__(self):
        self.transactions = 0
        self.commits = 0
        self.rollbacks = 0

    @contextmanager
    def transaction(self):
        self.transactions += 1
        try:
            yield object()
            self.commits += 1
        except Exception:
            self.rollbacks += 1
            raise


class AcademicFake:
    def __init__(self):
        self.subjects = {
            1: Subject(1, "SCI", "Science", True),
            2: Subject(2, "OLD", "Old subject", False),
        }
        self.years = {10: (10, "2026-2027", None, None, True)}
        self.assessments = {
            100: Assessment(
                100, 1, 10, "Midterm", 1, "MIDTERM", date(2026, 10, 1),
                AssessmentStatus.ACTIVE, NOW,
            )
        }
        self.scored = set()
        self.calls = []
        self.fail = False

    def list_subjects(self, _connection):
        return list(self.subjects.values())

    def list_active_subjects(self, _connection):
        return [
            (item.subject_id, item.subject_code, item.subject_name)
            for item in self.subjects.values() if item.is_active
        ]

    def get_subject_by_id(self, _connection, subject_id):
        return self.subjects.get(subject_id)

    def get_subject_by_code(self, _connection, code):
        item = next((x for x in self.subjects.values() if x.subject_code == code), None)
        return None if item is None else (
            item.subject_id, item.subject_code, item.subject_name, item.is_active
        )

    def create_subject(self, _connection, code, name, active):
        if self.fail:
            raise pyodbc.Error("raw SQL")
        identity = max(self.subjects) + 1
        self.subjects[identity] = Subject(identity, code, name, active)
        self.calls.append(("create_subject", code, name, active))
        return identity

    def update_subject(self, _connection, subject_id, code, name, active):
        if self.fail:
            raise pyodbc.Error("raw SQL")
        self.subjects[subject_id] = Subject(subject_id, code, name, active)
        self.calls.append(("update_subject", subject_id, code, name, active))

    def get_school_year_by_id(self, _connection, year_id):
        return self.years.get(year_id)

    def get_assessment_duplicate(self, _connection, year_id, subject_id, name):
        found = next((x for x in self.assessments.values() if (
            x.school_year_id, x.subject_id, x.assessment_name
        ) == (year_id, subject_id, name)), None)
        return None if found is None else found.assessment_id

    def create_assessment(self, _connection, subject_id, year_id, name, semester, kind, when):
        identity = max(self.assessments) + 1
        item = Assessment(
            identity, subject_id, year_id, name, semester, kind, when,
            AssessmentStatus.ACTIVE, NOW,
        )
        self.assessments[identity] = item
        self.calls.append(("create_assessment", subject_id, year_id, name))
        return item

    def get_assessment_by_id(self, _connection, assessment_id):
        return self.assessments.get(assessment_id)

    def assessment_has_scores(self, _connection, assessment_id):
        return assessment_id in self.scored

    def update_assessment(
        self, _connection, assessment_id, subject_id, year_id, name,
        semester, kind, when, status,
    ):
        current = self.assessments[assessment_id]
        self.assessments[assessment_id] = Assessment(
            assessment_id, subject_id, year_id, name, semester, kind, when,
            status, current.created_at,
        )
        self.calls.append(("update_assessment", assessment_id, subject_id, year_id, status))

    def list_assessments(self, _connection, year_id, subject_id=None, semester=None, status=None):
        return [item for item in self.assessments.values() if (
            item.school_year_id == year_id
            and (subject_id is None or item.subject_id == subject_id)
            and (semester is None or item.semester == semester)
            and (status is None or item.status == status)
        )]


class RuleFake:
    def __init__(self):
        self.rules = {}
        self.calls = []

    def list_rules(self, _connection, year_id, subject_id=None):
        return [item for item in self.rules.values() if (
            item.school_year_id == year_id
            and (subject_id is None or item.subject_id == subject_id)
        )]

    def get_active_rule(self, _connection, subject_id, year_id):
        return next((x for x in self.rules.values() if (
            x.subject_id == subject_id and x.school_year_id == year_id and x.is_active
        )), None)

    def get_by_id(self, _connection, rule_id):
        return self.rules.get(rule_id)

    def create(self, _connection, subject_id, year_id, threshold, active=True):
        identity = max(self.rules, default=0) + 1
        item = SupportRule(identity, subject_id, year_id, threshold, active, NOW, NOW)
        self.rules[identity] = item
        self.calls.append(("create", subject_id, year_id, threshold, active))
        return item

    def update_threshold(self, _connection, rule_id, threshold):
        item = self.rules.get(rule_id)
        if item is None:
            return None
        updated = SupportRule(
            item.rule_id, item.subject_id, item.school_year_id,
            threshold, item.is_active, item.created_at, NOW,
        )
        self.rules[rule_id] = updated
        return updated

    def set_active(self, _connection, rule_id, active):
        item = self.rules.get(rule_id)
        if item is None:
            return None
        updated = SupportRule(
            item.rule_id, item.subject_id, item.school_year_id,
            item.threshold, active, item.created_at, NOW,
        )
        self.rules[rule_id] = updated
        return updated


def build():
    db = FakeDatabase()
    academics = AcademicFake()
    rules = RuleFake()
    return AcademicService(db, academics, rules), db, academics, rules


def test_subject_list_create_update_and_deactivate_use_service_transactions():
    service, db, repo, _ = build()
    assert len(service.list_catalog_subjects()) == 2
    subject_id = service.create_subject("  art  ", "  Fine Art  ")
    service.update_subject(subject_id, "ART2", "Visual Art", True)
    service.set_subject_active(subject_id, False)
    assert repo.subjects[subject_id] == Subject(subject_id, "ART2", "Visual Art", False)
    assert db.transactions == 4


def test_inactive_subject_disappears_from_existing_active_selector():
    service, _, _, _ = build()
    service.set_subject_active(1, False)
    assert service.list_active_subjects() == []


def test_duplicate_subject_code_is_blocked_case_insensitively():
    service, _, _, _ = build()
    with pytest.raises(DuplicateError):
        service.create_subject(" sci ", "Duplicate")


@pytest.mark.parametrize("code,name", [("", "Name"), ("X", ""), ("X" * 21, "Name")])
def test_invalid_subject_text_is_blocked(code, name):
    service, db, _, _ = build()
    with pytest.raises(ValidationError):
        service.create_subject(code, name)
    assert db.transactions == 0


def test_subject_repository_error_is_normalized_and_rolled_back():
    service, db, repo, _ = build()
    repo.fail = True
    with pytest.raises(DatabaseError) as caught:
        service.create_subject("ART", "Art")
    assert "SQL" not in str(caught.value)
    assert db.rollbacks == 1


def test_assessment_create_validates_fk_duplicate_and_trims_values():
    service, _, repo, _ = build()
    created = service.create_assessment(
        1, 10, "  Final  ", 2, "  FINAL  ", date(2027, 5, 1)
    )
    assert created.assessment_name == "Final"
    assert created.assessment_type == "FINAL"
    with pytest.raises(DuplicateError):
        service.create_assessment(1, 10, "Final", 2, "FINAL", None)
    with pytest.raises(ValidationError):
        service.create_assessment(999, 10, "Other", 1, None, None)
    with pytest.raises(ValidationError):
        service.create_assessment(1, 999, "Other", 1, None, None)
    repo.subjects[1] = Subject(1, "SCI", "Science", False)
    with pytest.raises(BusinessRuleError):
        service.create_assessment(1, 10, "Inactive parent", 1, None, None)


def test_referenced_assessment_context_is_locked_but_safe_fields_can_change():
    service, _, repo, _ = build()
    repo.subjects[3] = Subject(3, "ART", "Art", True)
    repo.scored.add(100)
    with pytest.raises(BusinessRuleError):
        service.update_assessment(
            100, 3, 10, "Midterm", 1, "MIDTERM", None, AssessmentStatus.ACTIVE
        )
    service.update_assessment(
        100, 1, 10, "Midterm revised", 1, "QUIZ", None, AssessmentStatus.LOCKED
    )
    assert repo.assessments[100].assessment_name == "Midterm revised"
    assert repo.assessments[100].status == AssessmentStatus.LOCKED


def test_assessment_cancel_and_reactivate_preserve_identity():
    service, db, repo, _ = build()
    service.set_assessment_active(100, False)
    assert repo.assessments[100].status == AssessmentStatus.CANCELLED
    service.set_assessment_active(100, True)
    assert repo.assessments[100].status == AssessmentStatus.ACTIVE
    assert db.transactions == 2


def test_active_assessment_reader_excludes_cancelled_and_locked():
    service, _, repo, _ = build()
    repo.assessments[101] = Assessment(
        101, 1, 10, "Cancelled", None, None, None,
        AssessmentStatus.CANCELLED, NOW,
    )
    assert [x.assessment_id for x in service.list_active_assessments(10, 1)] == [100]


def test_inactive_subject_blocks_reactivating_assessment_or_rule():
    service, _, repo, _ = build()
    service.set_assessment_active(100, False)
    rule = service.create_support_rule(1, 10, Decimal("4.00"), False)
    repo.subjects[1] = Subject(1, "SCI", "Science", False)
    with pytest.raises(BusinessRuleError):
        service.set_assessment_active(100, True)
    with pytest.raises(BusinessRuleError):
        service.set_support_rule_active(rule.rule_id, True)


@pytest.mark.parametrize(
    "value",
    [Decimal("-0.01"), Decimal("10.01"), True, Decimal("NaN"),
     Decimal("Infinity"), Decimal("1.234")],
)
def test_invalid_support_rule_threshold_is_blocked(value):
    service, db, _, _ = build()
    with pytest.raises(ValidationError):
        service.create_support_rule(1, 10, value)
    assert db.transactions == 0


def test_support_rule_crud_keeps_decimal_and_scope():
    service, db, _, rules = build()
    rule = service.create_support_rule(1, 10, Decimal("4.25"))
    assert rule.threshold == Decimal("4.25")
    assert service.list_catalog_support_rules(10, 1) == [rule]
    updated = service.update_support_rule_threshold(rule.rule_id, Decimal("4.50"))
    assert updated.threshold == Decimal("4.50")
    inactive = service.set_support_rule_active(rule.rule_id, False)
    assert inactive.is_active is False
    assert rules.calls[0] == ("create", 1, 10, Decimal("4.25"), True)
    assert db.transactions == 4


def test_overlapping_active_rule_is_blocked_but_inactive_history_is_allowed():
    service, _, _, _ = build()
    first = service.create_support_rule(1, 10, Decimal("4.00"))
    with pytest.raises(DuplicateError):
        service.create_support_rule(1, 10, Decimal("5.00"))
    history = service.create_support_rule(1, 10, Decimal("3.00"), False)
    with pytest.raises(DuplicateError):
        service.set_support_rule_active(history.rule_id, True)
    service.set_support_rule_active(first.rule_id, False)
    assert service.set_support_rule_active(history.rule_id, True).is_active is True


def test_catalog_repositories_are_parameterized_and_never_commit():
    source = (inspect.getsource(AcademicRepository) + inspect.getsource(SupportRuleRepository)).upper()
    assert "SELECT *" not in source
    assert ".COMMIT(" not in source
    assert "WHERE SCHOOL_YEAR_ID = ?" in source
    assert "AND SUBJECT_ID = ?" in source


def test_catalog_backend_has_no_hard_coded_subject_or_threshold():
    source = inspect.getsource(AcademicService).upper()
    assert '"TOAN"' not in source
    assert '"VAN"' not in source
    assert "3.5" not in source
