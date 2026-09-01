from uuid import uuid4

from database.connection import DatabaseManager
from exceptions import DuplicateError, ValidationError
from models.dto import (
    Student,
    StudentCreateData,
    StudentUpdateData,
)
from models.enums import StudentStatus
from repositories import StudentRepository


class StudentService:
    def __init__(
        self,
        db: DatabaseManager,
        repository: StudentRepository | None = None,
    ):
        self.db = db
        self.repository = repository or StudentRepository()

    # =====================================================
    # CREATE
    # =====================================================

    def create_student(
        self,
        data: StudentCreateData,
    ) -> Student:
        self._validate_create_data(data)

        with self.db.transaction() as connection:
            existing = self.repository.get_by_code(
                connection,
                data.student_code,
            )

            if existing is not None:
                raise DuplicateError(
                    f"Mã học sinh '{data.student_code}' đã tồn tại."
                )

            student_id = self._generate_student_id()

            return self.repository.create(
                connection,
                student_id,
                data,
            )

    # =====================================================
    # READ
    # =====================================================

    def get_student(
        self,
        student_id: str,
    ) -> Student:
        if not student_id or not student_id.strip():
            raise ValidationError(
                "student_id không được để trống."
            )

        with self.db.transaction() as connection:
            student = self.repository.get_by_id(
                connection,
                student_id,
            )

            if student is None:
                raise ValidationError(
                    "Không tìm thấy học sinh."
                )

            return student

    def get_student_by_code(
        self,
        student_code: str,
    ) -> Student:
        if not student_code or not student_code.strip():
            raise ValidationError(
                "Mã học sinh không được để trống."
            )

        with self.db.transaction() as connection:
            student = self.repository.get_by_code(
                connection,
                student_code.strip(),
            )

            if student is None:
                raise ValidationError(
                    "Không tìm thấy học sinh."
                )

            return student

    def list_students(self) -> list[Student]:
        with self.db.transaction() as connection:
            return self.repository.list_all(connection)

    # =====================================================
    # UPDATE
    # =====================================================

    def update_student(
        self,
        student_id: str,
        data: StudentUpdateData,
    ) -> Student:
        if not student_id or not student_id.strip():
            raise ValidationError(
                "student_id không được để trống."
            )

        self._validate_update_data(data)

        with self.db.transaction() as connection:
            existing = self.repository.get_by_id(
                connection,
                student_id,
            )

            if existing is None:
                raise ValidationError(
                    "Không tìm thấy học sinh cần cập nhật."
                )

            updated = self.repository.update(
                connection,
                student_id,
                data,
            )

            if updated is None:
                raise ValidationError(
                    "Không thể cập nhật học sinh."
                )

            return updated

    # =====================================================
    # STATUS
    # =====================================================

    def deactivate_student(
        self,
        student_id: str,
    ) -> Student:
        return self._change_status(
            student_id,
            StudentStatus.INACTIVE,
        )

    def activate_student(
        self,
        student_id: str,
    ) -> Student:
        return self._change_status(
            student_id,
            StudentStatus.ACTIVE,
        )

    def _change_status(
        self,
        student_id: str,
        status: StudentStatus,
    ) -> Student:
        if not student_id or not student_id.strip():
            raise ValidationError(
                "student_id không được để trống."
            )

        with self.db.transaction() as connection:
            existing = self.repository.get_by_id(
                connection,
                student_id,
            )

            if existing is None:
                raise ValidationError(
                    "Không tìm thấy học sinh."
                )

            updated = self.repository.set_status(
                connection,
                student_id,
                status,
            )

            if updated is None:
                raise ValidationError(
                    "Không thể thay đổi trạng thái học sinh."
                )

            return updated

    # =====================================================
    # VALIDATION
    # =====================================================

    @staticmethod
    def _validate_create_data(
        data: StudentCreateData,
    ) -> None:
        if not data.student_code or not data.student_code.strip():
            raise ValidationError(
                "Mã học sinh không được để trống."
            )

        if not data.full_name or not data.full_name.strip():
            raise ValidationError(
                "Họ tên học sinh không được để trống."
            )

    @staticmethod
    def _validate_update_data(
        data: StudentUpdateData,
    ) -> None:
        if not data.full_name or not data.full_name.strip():
            raise ValidationError(
                "Họ tên học sinh không được để trống."
            )

    # =====================================================
    # ID
    # =====================================================

    @staticmethod
    def _generate_student_id() -> str:
        return uuid4().hex[:20]