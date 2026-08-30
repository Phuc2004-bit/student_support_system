from dataclasses import FrozenInstanceError
from datetime import date, datetime

import pytest

from models.dto import (
    Enrollment,
    Student,
    StudentCreateData,
)
from models.enums import (
    EnrollmentStatus,
    StudentStatus,
)


def test_create_student_dto():
    now = datetime.now()

    student = Student(
        student_id="student-001",
        student_code="HS001",
        full_name="Nguyễn Văn A",
        date_of_birth=date(2010, 5, 20),
        gender="Nam",
        phone=None,
        email=None,
        address=None,
        status=StudentStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )

    assert student.student_code == "HS001"
    assert student.full_name == "Nguyễn Văn A"
    assert student.status == StudentStatus.ACTIVE


def test_student_create_data_optional_fields():
    data = StudentCreateData(
        student_code="HS002",
        full_name="Trần Thị B",
    )

    assert data.date_of_birth is None
    assert data.phone is None
    assert data.email is None


def test_create_enrollment_dto():
    enrollment = Enrollment(
        enrollment_id=1,
        student_id="student-001",
        class_id=10,
        enrollment_date=date(2026, 9, 7),
        status=EnrollmentStatus.ACTIVE,
        created_at=datetime.now(),
    )

    assert enrollment.student_id == "student-001"
    assert enrollment.class_id == 10
    assert enrollment.status == EnrollmentStatus.ACTIVE


def test_student_dto_is_immutable():
    now = datetime.now()

    student = Student(
        student_id="student-001",
        student_code="HS001",
        full_name="Nguyễn Văn A",
        date_of_birth=None,
        gender=None,
        phone=None,
        email=None,
        address=None,
        status=StudentStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )

    with pytest.raises(FrozenInstanceError):
        student.full_name = "Tên khác"