from datetime import date

from database.connection import DatabaseManager
from exceptions import (
    BusinessRuleError,
    ValidationError,
)
from models.dto import Enrollment, EnrollmentListItem
from models.enums import (
    EnrollmentStatus,
    StudentStatus,
)
from repositories import (
    AcademicRepository,
    EnrollmentRepository,
    StudentRepository,
)


class EnrollmentService:
    def __init__(
        self,
        db: DatabaseManager,
        enrollment_repository: EnrollmentRepository | None = None,
        student_repository: StudentRepository | None = None,
        academic_repository: AcademicRepository | None = None,
    ):
        self.db = db

        self.enrollment_repository = (
            enrollment_repository
            or EnrollmentRepository()
        )

        self.student_repository = (
            student_repository
            or StudentRepository()
        )

        self.academic_repository = (
            academic_repository
            or AcademicRepository()
        )

    # =====================================================
    # CREATE FIRST ENROLLMENT
    # =====================================================

    def enroll_student(
        self,
        student_id: str,
        class_id: int,
        enrollment_date: date,
    ) -> Enrollment:
        self._validate_basic_input(
            student_id,
            class_id,
            enrollment_date,
        )

        with self.db.transaction() as connection:
            student = self.student_repository.get_by_id(
                connection,
                student_id,
            )

            if student is None:
                raise ValidationError(
                    "Không tìm thấy học sinh."
                )

            if student.status != StudentStatus.ACTIVE:
                raise BusinessRuleError(
                    "Học sinh không ở trạng thái hoạt động."
                )

            class_info = self.academic_repository.get_class_by_id(
                connection,
                class_id,
            )

            if class_info is None:
                raise ValidationError(
                    "Không tìm thấy lớp học."
                )

            current = (
                self.enrollment_repository
                .get_active_by_student(
                    connection,
                    student_id,
                )
            )

            if current is not None:
                raise BusinessRuleError(
                    "Học sinh đã có lớp đang hoạt động. "
                    "Hãy sử dụng chức năng chuyển lớp."
                )

            return self.enrollment_repository.create(
                connection,
                student_id,
                class_id,
                enrollment_date,
            )

    # =====================================================
    # TRANSFER
    # =====================================================

    def transfer_student(
        self,
        student_id: str,
        new_class_id: int,
        transfer_date: date,
    ) -> Enrollment:
        self._validate_basic_input(
            student_id,
            new_class_id,
            transfer_date,
        )

        with self.db.transaction() as connection:
            student = self.student_repository.get_by_id(
                connection,
                student_id,
            )

            if student is None:
                raise ValidationError(
                    "Không tìm thấy học sinh."
                )

            if student.status != StudentStatus.ACTIVE:
                raise BusinessRuleError(
                    "Học sinh không ở trạng thái hoạt động."
                )

            new_class = (
                self.academic_repository.get_class_by_id(
                    connection,
                    new_class_id,
                )
            )

            if new_class is None:
                raise ValidationError(
                    "Không tìm thấy lớp mới."
                )

            current = (
                self.enrollment_repository
                .get_active_by_student(
                    connection,
                    student_id,
                )
            )

            if current is None:
                raise BusinessRuleError(
                    "Học sinh chưa có lớp đang hoạt động."
                )

            if current.class_id == new_class_id:
                raise BusinessRuleError(
                    "Lớp mới trùng với lớp hiện tại."
                )

            old_enrollment = (
                self.enrollment_repository.set_status(
                    connection,
                    current.enrollment_id,
                    EnrollmentStatus.TRANSFERRED,
                )
            )

            if old_enrollment is None:
                raise BusinessRuleError(
                    "Không thể kết thúc enrollment hiện tại."
                )

            return self.enrollment_repository.create(
                connection,
                student_id,
                new_class_id,
                transfer_date,
            )

    # =====================================================
    # READ
    # =====================================================

    def get_active_enrollment(
        self,
        student_id: str,
    ) -> Enrollment | None:
        if not student_id or not student_id.strip():
            raise ValidationError(
                "student_id không được để trống."
            )

        with self.db.transaction() as connection:
            return (
                self.enrollment_repository
                .get_active_by_student(
                    connection,
                    student_id,
                )
            )

    def get_student_history(
        self,
        student_id: str,
    ) -> list[EnrollmentListItem]:
        if not student_id or not student_id.strip():
            raise ValidationError(
                "student_id không được để trống."
            )

        with self.db.transaction() as connection:
            student = self.student_repository.get_by_id(
                connection,
                student_id,
            )

            if student is None:
                raise ValidationError(
                    "Không tìm thấy học sinh."
                )

            return self.enrollment_repository.list_by_student(
                connection,
                student_id,
            )

    def list_class_enrollments(
        self,
        class_id: int,
        school_year_id: int,
    ) -> list[EnrollmentListItem]:
        self._validate_positive_id("class_id", class_id)
        self._validate_positive_id(
            "school_year_id",
            school_year_id,
        )

        with self.db.transaction() as connection:
            return self.enrollment_repository.list_by_class(
                connection,
                class_id,
                school_year_id,
                EnrollmentStatus.ACTIVE,
            )

    # =====================================================
    # VALIDATION
    # =====================================================

    @staticmethod
    def _validate_basic_input(
        student_id: str,
        class_id: int,
        action_date: date,
    ) -> None:
        if not student_id or not student_id.strip():
            raise ValidationError(
                "student_id không được để trống."
            )

        if class_id <= 0:
            raise ValidationError(
                "class_id không hợp lệ."
            )

        if action_date is None:
            raise ValidationError(
                "Ngày nhập học/chuyển lớp không được để trống."
            )

    @staticmethod
    def _validate_positive_id(
        field_name: str,
        value: int,
    ) -> None:
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value <= 0
        ):
            raise ValidationError(
                f"{field_name} không hợp lệ."
            )
