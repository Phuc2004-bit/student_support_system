from __future__ import annotations
from database.connection import DatabaseManager
from exceptions import ValidationError
from models.dto.student_filter import StudentFilter
from models.dto.student_list import StudentListItem
from repositories.student_list_repository import StudentListRepository

class StudentListService:
    def __init__(self, db: DatabaseManager, repository: StudentListRepository | None = None):
        self.db=db
        self.repository=repository or StudentListRepository()

    def list_students(self, filters: StudentFilter | None = None) -> list[StudentListItem]:
        filters=filters or StudentFilter()
        self._validate(filters)
        with self.db.transaction() as connection:
            return self.repository.list_students(connection, filters)

    @staticmethod
    def _validate(filters: StudentFilter) -> None:
        for name in ("school_year_id","grade_id","class_id"):
            value=getattr(filters,name)
            if value is not None and (isinstance(value,bool) or not isinstance(value,int) or value <= 0):
                raise ValidationError(f"{name} không hợp lệ.")
