from contextlib import contextmanager
from datetime import date
from decimal import Decimal
import inspect

import pytest

from exceptions import ValidationError
from models.dto.report_dto import SupportReportRow
from models.enums import InterventionStatus
from repositories.intervention_repository import InterventionRepository
from repositories.report_repository import ReportRepository
from services.report_service import ReportService
from services.support_read_contract import SupportReadServiceContract
from tests.test_report_repository_integration import (
    cleanup,
    get_test_db,
    seed_report_data,
)


class RecordingCursor:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def execute(self, sql, *params):
        self.calls.append((sql, params))
        return self

    def fetchall(self):
        return list(self.rows)


class RecordingConnection:
    def __init__(self, rows):
        self.recording_cursor = RecordingCursor(rows)

    def cursor(self):
        return self.recording_cursor


class FakeDatabase:
    def __init__(self):
        self.connection = object()
        self.transaction_count = 0

    @contextmanager
    def transaction(self):
        self.transaction_count += 1
        yield self.connection


class FakeReportRepository:
    def __init__(self):
        self.calls = []

    def list_support_cases(self, **kwargs):
        self.calls.append(kwargs)
        return []


def support_row_tuple():
    return (
        101,
        "HS001",
        "Nguyen Van A",
        10,
        "10A1",
        "MATH",
        "Mathematics",
        date(2026, 10, 10),
        date(2026, 10, 12),
        "COMPLETED",
        Decimal("2.80"),
        date(2026, 11, 20),
        Decimal("4.20"),
        "PASSED",
        "student-101",
        201,
        10,
        301,
        401,
        501,
        "Teacher A",
    )


def test_support_read_contract_matches_existing_report_service_api():
    contract_signature = inspect.signature(
        SupportReadServiceContract.get_support_cases
    )
    service_signature = inspect.signature(
        ReportService.get_support_cases
    )

    assert contract_signature == service_signature


def test_support_report_row_remains_backward_compatible():
    row = SupportReportRow(
        intervention_id=1,
        student_code="HS001",
        full_name="Student A",
        grade_number=10,
        class_name="10A1",
        subject_code="MATH",
        subject_name="Mathematics",
        detected_date=date(2026, 10, 10),
        start_date=None,
        status="DETECTED",
        trigger_score=Decimal("2.50"),
    )

    assert row.student_id is None
    assert row.enrollment_id is None
    assert row.subject_id is None
    assert row.responsible_user_id is None


def test_repository_maps_complete_support_read_model_in_one_query():
    connection = RecordingConnection([support_row_tuple()])

    rows = ReportRepository().list_support_cases(
        connection=connection,
        school_year_id=1,
        grade_id=10,
        class_id=301,
        subject_id=401,
        status="COMPLETED",
    )

    assert len(connection.recording_cursor.calls) == 1
    sql, params = connection.recording_cursor.calls[0]
    normalized_sql = " ".join(sql.upper().split())

    assert "SELECT *" not in normalized_sql
    assert "OUTER APPLY" in normalized_sql
    assert "TOP (1)" in normalized_sql
    assert "LEFT JOIN DBO.USERS" in normalized_sql
    assert params == (1, 10, 301, 401, "COMPLETED")

    row = rows[0]
    assert row.intervention_id == 101
    assert row.student_id == "student-101"
    assert row.enrollment_id == 201
    assert row.grade_id == 10
    assert row.class_id == 301
    assert row.subject_id == 401
    assert row.responsible_user_id == 501
    assert row.responsible_user_name == "Teacher A"
    assert row.trigger_score == Decimal("2.80")
    assert row.latest_review_score == Decimal("4.20")


def test_repository_empty_result_is_an_empty_list():
    connection = RecordingConnection([])

    assert ReportRepository().list_support_cases(
        connection=connection,
        school_year_id=1,
    ) == []


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("school_year_id", 0),
        ("school_year_id", True),
        ("grade_id", -1),
        ("class_id", "1"),
        ("subject_id", 0),
        ("status", "OPEN"),
    ],
)
def test_support_read_rejects_invalid_filters_before_database_access(
    field,
    value,
):
    db = FakeDatabase()
    repository = FakeReportRepository()
    service = ReportService(db=db, report_repository=repository)
    filters = {"school_year_id": 1, field: value}

    with pytest.raises(ValidationError):
        service.get_support_cases(**filters)

    assert db.transaction_count == 0
    assert repository.calls == []


def test_real_support_read_filters_mapping_latest_review_and_read_only():
    test_db = get_test_db()
    cleanup(test_db)

    try:
        seeded = seed_report_data(test_db)
        service = ReportService(db=test_db)
        intervention_repository = InterventionRepository()
        intervention_ids = (
            seeded["completed_intervention_id"],
            seeded["detected_intervention_id"],
        )

        with test_db.transaction() as connection:
            statuses_before = {
                intervention_id: intervention_repository.get_by_id(
                    connection,
                    intervention_id,
                ).status
                for intervention_id in intervention_ids
            }

        all_rows = service.get_support_cases(
            school_year_id=seeded["school_year_id"]
        )
        grade_rows = service.get_support_cases(
            school_year_id=seeded["school_year_id"],
            grade_id=seeded["grade_id"],
        )
        class_rows = service.get_support_cases(
            school_year_id=seeded["school_year_id"],
            class_id=seeded["class_id"],
        )
        subject_rows = service.get_support_cases(
            school_year_id=seeded["school_year_id"],
            subject_id=seeded["subject_id"],
        )
        detected_rows = service.get_support_cases(
            school_year_id=seeded["school_year_id"],
            status=InterventionStatus.DETECTED,
        )
        completed_rows = service.get_support_cases(
            school_year_id=seeded["school_year_id"],
            status=InterventionStatus.COMPLETED,
        )
        empty_rows = service.get_support_cases(
            school_year_id=seeded["school_year_id"],
            subject_id=2_147_483_647,
        )

        assert len(all_rows) == 2
        assert len({row.intervention_id for row in all_rows}) == 2
        assert len(grade_rows) == 2
        assert len(class_rows) == 2
        assert len(subject_rows) == 2
        assert [row.status for row in detected_rows] == ["DETECTED"]
        assert [row.status for row in completed_rows] == ["COMPLETED"]
        assert empty_rows == []

        completed = completed_rows[0]
        assert completed.student_id is not None
        assert completed.enrollment_id is not None
        assert completed.student_code == "TRPT_HS001"
        assert completed.grade_id == seeded["grade_id"]
        assert completed.grade_number == 10
        assert completed.class_id == seeded["class_id"]
        assert completed.class_name == "TRPT_10A1"
        assert completed.subject_id == seeded["subject_id"]
        assert completed.subject_code == "TRPT_TOAN"
        assert completed.trigger_score == Decimal("2.80")
        assert completed.latest_review_date == date(2026, 11, 20)
        assert completed.latest_review_score == Decimal("4.20")
        assert completed.latest_review_result == "PASSED"

        with test_db.transaction() as connection:
            statuses_after = {
                intervention_id: intervention_repository.get_by_id(
                    connection,
                    intervention_id,
                ).status
                for intervention_id in intervention_ids
            }

        assert statuses_after == statuses_before
    finally:
        cleanup(test_db)
