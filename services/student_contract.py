from __future__ import annotations

from typing import Protocol

from models.dto import Student, StudentCreateData, StudentUpdateData
from models.dto.student_filter import StudentFilter
from models.dto.student_list import StudentListItem


class StudentServiceContract(Protocol):
    def list_students(self) -> list[Student]:
        ...

    def get_student(self, student_id: str) -> Student:
        ...

    def create_student(self, data: StudentCreateData) -> Student:
        ...

    def update_student(
        self,
        student_id: str,
        data: StudentUpdateData,
    ) -> Student:
        ...


class StudentListServiceContract(Protocol):
    def list_students(
        self,
        filters: StudentFilter | None = None,
    ) -> list[StudentListItem]:
        ...
