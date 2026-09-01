from contextlib import contextmanager
from datetime import date
from decimal import Decimal

import pytest

from exceptions import ValidationError
from models.dto.dashboard_dto import (
    DashboardAttentionItem,
    DashboardStatusItem,
    DashboardSummary,
)
from services.dashboard_service import DashboardService


class FakeDatabase:
    def __init__(self):
        self.connection = object()
        self.transaction_count = 0

    @contextmanager
    def transaction(self):
        self.transaction_count += 1
        yield self.connection


class FakeDashboardRepository:
    def __init__(self):
        self.calls = []

    def get_summary(self, **kwargs):
        self.calls.append(
            ("summary", kwargs)
        )
        return DashboardSummary(
            total_students=1000,
            needs_support_count=120,
            in_progress_count=50,
            waiting_review_count=20,
            completed_count=40,
            continue_count=10,
        )

    def get_status_breakdown(self, **kwargs):
        self.calls.append(
            ("breakdown", kwargs)
        )
        return [
            DashboardStatusItem(
                status="IN_PROGRESS",
                count=50,
            )
        ]

    def list_attention_items(self, **kwargs):
        self.calls.append(
            ("attention", kwargs)
        )
        return [
            DashboardAttentionItem(
                intervention_id=1,
                student_code="HS001",
                full_name="Học sinh A",
                grade_number=10,
                class_name="10A1",
                subject_code="TOAN",
                subject_name="Toán",
                status="WAITING_REVIEW",
                detected_date=date(2026, 9, 1),
                trigger_score=Decimal("2.80"),
            )
        ]


def make_service():
    db = FakeDatabase()
    repository = FakeDashboardRepository()

    service = DashboardService(
        db=db,
        dashboard_repository=repository,
    )

    return service, db, repository


def test_get_dashboard_uses_one_transaction_for_whole_snapshot():
    service, db, repository = make_service()

    data = service.get_dashboard(
        school_year_id=1,
        grade_id=5,
        class_id=12,
        subject_id=2,
    )

    assert db.transaction_count == 1
    assert data.summary.total_students == 1000
    assert len(data.status_breakdown) == 1
    assert len(data.attention_items) == 1

    assert [
        name
        for name, _ in repository.calls
    ] == [
        "summary",
        "breakdown",
        "attention",
    ]


def test_get_dashboard_passes_same_filters_to_all_repository_calls():
    service, db, repository = make_service()

    service.get_dashboard(
        school_year_id=3,
        grade_id=7,
        class_id=20,
        subject_id=1,
    )

    for _, kwargs in repository.calls:
        assert kwargs["connection"] is db.connection
        assert kwargs["school_year_id"] == 3
        assert kwargs["grade_id"] == 7
        assert kwargs["class_id"] == 20
        assert kwargs["subject_id"] == 1


@pytest.mark.parametrize(
    "field,value",
    [
        ("school_year_id", 0),
        ("school_year_id", -1),
        ("school_year_id", True),
        ("school_year_id", "1"),
        ("grade_id", 0),
        ("class_id", -2),
        ("subject_id", False),
    ],
)
def test_invalid_filter_ids_are_rejected(field, value):
    service, _, _ = make_service()

    kwargs = {
        "school_year_id": 1,
        "grade_id": None,
        "class_id": None,
        "subject_id": None,
    }
    kwargs[field] = value

    with pytest.raises(ValidationError):
        service.get_dashboard(**kwargs)


def test_school_year_is_required():
    service, _, _ = make_service()

    with pytest.raises(ValidationError):
        service.get_dashboard(
            school_year_id=None,
        )
