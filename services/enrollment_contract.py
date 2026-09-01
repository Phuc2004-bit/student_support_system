from __future__ import annotations

from datetime import date
from typing import Protocol

from models.dto.enrollment import Enrollment, EnrollmentListItem


class EnrollmentServiceContract(Protocol):
    def enroll_student(
        self,
        student_id: str,
        class_id: int,
        enrollment_date: date,
    ) -> Enrollment:
        ...

    def transfer_student(
        self,
        student_id: str,
        new_class_id: int,
        transfer_date: date,
    ) -> Enrollment:
        ...

    def get_active_enrollment(
        self,
        student_id: str,
    ) -> Enrollment | None:
        ...

    def get_student_history(
        self,
        student_id: str,
    ) -> list[EnrollmentListItem]:
        ...
