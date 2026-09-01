from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal

from models.dto import (
    EnrollmentListItem,
    InterventionHistoryItem,
    ScoreListItem,
    Student,
)
from models.enums import EnrollmentStatus, InterventionStatus, StudentStatus
from services.student_profile_service import StudentProfileService


class Database:
    def __init__(self):
        self.connection = object()
        self.transactions = 0

    @contextmanager
    def transaction(self):
        self.transactions += 1
        yield self.connection


class StudentRepository:
    def get_by_id(self, connection, student_id):
        assert connection is database.connection
        assert student_id == "student-1"
        return Student(
            "student-1", "HS001", "Nguyễn Văn A", date(2012, 1, 2),
            "Nam", None, None, None, StudentStatus.ACTIVE,
            datetime(2026, 1, 1), datetime(2026, 1, 1),
        )


class EnrollmentRepository:
    def list_by_student(self, connection, student_id):
        assert connection is database.connection
        return [EnrollmentListItem(
            1, student_id, "HS001", "Nguyễn Văn A", 10, "6A1", 6,
            1, "2026-2027", EnrollmentStatus.ACTIVE,
        )]


class ScoreRepository:
    def list_by_student(self, connection, student_id):
        assert connection is database.connection
        return [ScoreListItem(
            1, 1, student_id, "HS001", "Nguyễn Văn A", "6A1",
            "Toán", "Giữa kỳ", Decimal("8.50"),
        )]


class InterventionRepository:
    def list_by_student(self, connection, student_id):
        assert connection is database.connection
        return [InterventionHistoryItem(
            1, 1, student_id, "6A1", "Toán", Decimal("3.00"),
            date(2026, 10, 1), InterventionStatus.COMPLETED,
            "Phụ đạo nhóm",
        )]


database = Database()


def test_get_profile_reads_all_saved_history_in_one_transaction():
    service = StudentProfileService(
        database,
        StudentRepository(),
        EnrollmentRepository(),
        ScoreRepository(),
        InterventionRepository(),
    )

    profile = service.get_profile("student-1")

    assert database.transactions == 1
    assert profile.student.full_name == "Nguyễn Văn A"
    assert profile.enrollment_history[0].class_name == "6A1"
    assert profile.score_history[0].assessment_name == "Giữa kỳ"
    assert (
        profile.intervention_history[0].status
        == InterventionStatus.COMPLETED
    )
