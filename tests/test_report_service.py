from contextlib import contextmanager
from datetime import date
from decimal import Decimal

import pytest

from exceptions import ValidationError
from models.dto.report_dto import (
    SupportReportRow,
    SupportReportSummary,
)
from models.enums import InterventionStatus
from services.report_service import ReportService


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
        self.list_calls = []
        self.summary_calls = []

        self.rows = [
            SupportReportRow(
                intervention_id=101,
                student_code="HS001",
                full_name="Nguyễn Văn A",
                grade_number=10,
                class_name="10A1",
                subject_code="TOAN",
                subject_name="Toán",
                detected_date=date(2026, 10, 10),
                start_date=date(2026, 10, 12),
                status="COMPLETED",
                trigger_score=Decimal("2.80"),
                latest_review_date=date(2026, 11, 20),
                latest_review_score=Decimal("4.20"),
                latest_review_result="PASSED",
            )
        ]

        self.summary = SupportReportSummary(
            total_cases=1,
            detected_count=0,
            planned_count=0,
            in_progress_count=0,
            waiting_review_count=0,
            continue_count=0,
            completed_count=1,
        )

    def list_support_cases(
        self,
        connection,
        school_year_id,
        grade_id=None,
        class_id=None,
        subject_id=None,
        status=None,
    ):
        self.list_calls.append(
            {
                "connection": connection,
                "school_year_id": school_year_id,
                "grade_id": grade_id,
                "class_id": class_id,
                "subject_id": subject_id,
                "status": status,
            }
        )
        return list(self.rows)

    def get_support_summary(
        self,
        connection,
        school_year_id,
        grade_id=None,
        class_id=None,
        subject_id=None,
    ):
        self.summary_calls.append(
            {
                "connection": connection,
                "school_year_id": school_year_id,
                "grade_id": grade_id,
                "class_id": class_id,
                "subject_id": subject_id,
            }
        )
        return self.summary


def test_get_support_report_returns_summary_and_rows_in_one_transaction():
    db = FakeDatabase()
    repo = FakeReportRepository()
    service = ReportService(
        db=db,
        report_repository=repo,
    )

    result = service.get_support_report(
        school_year_id=1,
        grade_id=10,
        class_id=100,
        subject_id=5,
        status=InterventionStatus.COMPLETED,
    )

    assert db.transaction_count == 1

    assert result.summary.total_cases == 1
    assert result.summary.completed_count == 1
    assert len(result.rows) == 1
    assert result.rows[0].latest_review_score == Decimal("4.20")
    assert result.rows[0].latest_review_result == "PASSED"

    assert len(repo.summary_calls) == 1
    assert len(repo.list_calls) == 1

    assert repo.list_calls[0]["status"] == "COMPLETED"
    assert repo.list_calls[0]["school_year_id"] == 1
    assert repo.list_calls[0]["grade_id"] == 10
    assert repo.list_calls[0]["class_id"] == 100
    assert repo.list_calls[0]["subject_id"] == 5

    # Hai repository call phải dùng cùng connection của transaction.
    assert (
        repo.summary_calls[0]["connection"]
        is repo.list_calls[0]["connection"]
    )


def test_string_status_is_normalized_before_repository_call():
    db = FakeDatabase()
    repo = FakeReportRepository()
    service = ReportService(
        db=db,
        report_repository=repo,
    )

    rows = service.get_support_cases(
        school_year_id=1,
        status="  completed  ",
    )

    assert len(rows) == 1
    assert repo.list_calls[0]["status"] == "COMPLETED"


def test_invalid_filters_raise_validation_error_before_transaction():
    db = FakeDatabase()
    repo = FakeReportRepository()
    service = ReportService(
        db=db,
        report_repository=repo,
    )

    invalid_calls = (
        lambda: service.get_support_cases(
            school_year_id=0,
        ),
        lambda: service.get_support_cases(
            school_year_id=1,
            grade_id=-1,
        ),
        lambda: service.get_support_cases(
            school_year_id=1,
            class_id=True,
        ),
        lambda: service.get_support_cases(
            school_year_id=1,
            status="UNKNOWN_STATUS",
        ),
    )

    for call in invalid_calls:
        with pytest.raises(ValidationError):
            call()

    assert db.transaction_count == 0
    assert repo.list_calls == []
    assert repo.summary_calls == []


def test_empty_report_is_returned_cleanly():
    db = FakeDatabase()
    repo = FakeReportRepository()

    repo.rows = []
    repo.summary = SupportReportSummary(
        total_cases=0,
        detected_count=0,
        planned_count=0,
        in_progress_count=0,
        waiting_review_count=0,
        continue_count=0,
        completed_count=0,
    )

    service = ReportService(
        db=db,
        report_repository=repo,
    )

    result = service.get_support_report(
        school_year_id=1,
    )

    assert db.transaction_count == 1
    assert result.summary.total_cases == 0
    assert result.rows == ()
