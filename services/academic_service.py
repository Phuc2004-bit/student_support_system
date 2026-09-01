from datetime import date

from database.connection import DatabaseManager
from exceptions import DuplicateError, ValidationError
from models.dto import Assessment
from repositories import AcademicRepository


class AcademicService:
    def __init__(
        self,
        db: DatabaseManager,
        repository: AcademicRepository | None = None,
    ):
        self.db = db
        self.repository = repository or AcademicRepository()

    # =====================================================
    # SCHOOL YEAR
    # =====================================================

    def list_school_years(self) -> list[tuple]:
        with self.db.transaction() as connection:
            return self.repository.list_school_years(
                connection
            )

    def list_grades(self) -> list[tuple[int, int, str | None]]:
        with self.db.transaction() as connection:
            return self.repository.list_grades(
                connection
            )

    def create_school_year(
        self,
        year_name: str,
        start_date: date,
        end_date: date,
        is_current: bool = False,
    ) -> int:
        if not year_name or not year_name.strip():
            raise ValidationError(
                "Tên năm học không được để trống."
            )

        if start_date is None or end_date is None:
            raise ValidationError(
                "Ngày bắt đầu và ngày kết thúc không được để trống."
            )

        if start_date >= end_date:
            raise ValidationError(
                "Ngày bắt đầu phải nhỏ hơn ngày kết thúc."
            )

        with self.db.transaction() as connection:
            existing = self.repository.get_school_year_by_name(
                connection,
                year_name.strip(),
            )

            if existing is not None:
                raise DuplicateError(
                    f"Năm học '{year_name}' đã tồn tại."
                )

            return self.repository.create_school_year(
                connection,
                year_name.strip(),
                start_date,
                end_date,
                is_current,
            )

    def get_school_year(
        self,
        year_name: str,
    ):
        if not year_name or not year_name.strip():
            raise ValidationError(
                "Tên năm học không được để trống."
            )

        with self.db.transaction() as connection:
            result = self.repository.get_school_year_by_name(
                connection,
                year_name.strip(),
            )

            if result is None:
                raise ValidationError(
                    "Không tìm thấy năm học."
                )

            return result

    # =====================================================
    # CLASS
    # =====================================================

    def create_class(
        self,
        class_name: str,
        grade_id: int,
        school_year_id: int,
        homeroom_teacher: str | None = None,
    ) -> int:
        if not class_name or not class_name.strip():
            raise ValidationError(
                "Tên lớp không được để trống."
            )

        if grade_id <= 0:
            raise ValidationError(
                "grade_id không hợp lệ."
            )

        if school_year_id <= 0:
            raise ValidationError(
                "school_year_id không hợp lệ."
            )

        with self.db.transaction() as connection:
            return self.repository.create_class(
                connection,
                class_name.strip(),
                grade_id,
                school_year_id,
                homeroom_teacher,
            )

    def get_class(
        self,
        class_id: int,
    ):
        if class_id <= 0:
            raise ValidationError(
                "class_id không hợp lệ."
            )

        with self.db.transaction() as connection:
            result = self.repository.get_class_by_id(
                connection,
                class_id,
            )

            if result is None:
                raise ValidationError(
                    "Không tìm thấy lớp học."
                )

            return result

    def list_classes_by_school_year(
        self,
        school_year_id: int,
    ) -> list[tuple]:
        if school_year_id <= 0:
            raise ValidationError(
                "school_year_id không hợp lệ."
            )

        with self.db.transaction() as connection:
            return self.repository.list_classes_by_school_year(
                connection,
                school_year_id,
            )

    # =====================================================
    # SUBJECT
    # =====================================================

    def create_subject(
        self,
        subject_code: str,
        subject_name: str,
    ) -> int:
        if not subject_code or not subject_code.strip():
            raise ValidationError(
                "Mã môn học không được để trống."
            )

        if not subject_name or not subject_name.strip():
            raise ValidationError(
                "Tên môn học không được để trống."
            )

        normalized_code = subject_code.strip().upper()

        with self.db.transaction() as connection:
            existing = self.repository.get_subject_by_code(
                connection,
                normalized_code,
            )

            if existing is not None:
                raise DuplicateError(
                    f"Mã môn học '{normalized_code}' đã tồn tại."
                )

            return self.repository.create_subject(
                connection,
                normalized_code,
                subject_name.strip(),
                True,
            )

    def get_subject(
        self,
        subject_code: str,
    ):
        if not subject_code or not subject_code.strip():
            raise ValidationError(
                "Mã môn học không được để trống."
            )

        with self.db.transaction() as connection:
            result = self.repository.get_subject_by_code(
                connection,
                subject_code.strip().upper(),
            )

            if result is None:
                raise ValidationError(
                    "Không tìm thấy môn học."
                )

            return result

    def list_active_subjects(self) -> list[tuple]:
        with self.db.transaction() as connection:
            return self.repository.list_active_subjects(
                connection
            )

    # =====================================================
    # ASSESSMENT
    # =====================================================

    def create_assessment(
        self,
        subject_id: int,
        school_year_id: int,
        assessment_name: str,
        semester: int | None,
        assessment_type: str | None,
        assessment_date: date | None,
    ) -> Assessment:
        if subject_id <= 0:
            raise ValidationError(
                "subject_id không hợp lệ."
            )

        if school_year_id <= 0:
            raise ValidationError(
                "school_year_id không hợp lệ."
            )

        if not assessment_name or not assessment_name.strip():
            raise ValidationError(
                "Tên bài đánh giá không được để trống."
            )

        if semester is not None and semester not in (1, 2):
            raise ValidationError(
                "Học kỳ chỉ được là 1 hoặc 2."
            )

        with self.db.transaction() as connection:
            return self.repository.create_assessment(
                connection,
                subject_id,
                school_year_id,
                assessment_name.strip(),
                semester,
                assessment_type,
                assessment_date,
            )

    def get_assessment(
        self,
        assessment_id: int,
    ) -> Assessment:
        if assessment_id <= 0:
            raise ValidationError(
                "assessment_id không hợp lệ."
            )

        with self.db.transaction() as connection:
            assessment = self.repository.get_assessment_by_id(
                connection,
                assessment_id,
            )

            if assessment is None:
                raise ValidationError(
                    "Không tìm thấy bài đánh giá."
                )

            return assessment