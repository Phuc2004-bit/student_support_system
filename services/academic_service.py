from datetime import date

from database.connection import DatabaseManager
from exceptions import BusinessRuleError, DuplicateError, ValidationError
from models.dto import Assessment, Grade, SchoolClass, SchoolYear
from models.enums import AssessmentStatus
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

    def list_catalog_school_years(self) -> list[SchoolYear]:
        return [SchoolYear(*item) for item in self.list_school_years()]

    def list_catalog_grades(self) -> list[Grade]:
        return [Grade(*item) for item in self.list_grades()]

    def create_grade(
        self,
        grade_number: int,
        grade_name: str | None = None,
    ) -> int:
        self._validate_grade_number(grade_number)
        normalized_name = self._normalize_optional_text(
            grade_name,
            "Tên khối",
            30,
        )
        with self.db.transaction() as connection:
            if self.repository.get_grade_by_number(
                connection,
                grade_number,
            ) is not None:
                raise DuplicateError(
                    f"Khối {grade_number} đã tồn tại."
                )
            return self.repository.create_grade(
                connection,
                grade_number,
                normalized_name,
            )

    def update_grade_name(
        self,
        grade_id: int,
        grade_name: str | None,
    ) -> None:
        self._validate_positive_id("grade_id", grade_id)
        normalized_name = self._normalize_optional_text(
            grade_name,
            "Tên khối",
            30,
        )
        with self.db.transaction() as connection:
            if self.repository.get_grade_by_id(
                connection,
                grade_id,
            ) is None:
                raise ValidationError("Không tìm thấy khối.")
            self.repository.update_grade_name(
                connection,
                grade_id,
                normalized_name,
            )

    def create_school_year(
        self,
        year_name: str,
        start_date: date,
        end_date: date,
        is_current: bool = False,
    ) -> int:
        year_name = self._validate_school_year_data(
            year_name,
            start_date,
            end_date,
            is_current,
        )
        with self.db.transaction() as connection:
            existing = self.repository.get_school_year_by_name(
                connection,
                year_name,
            )
            if existing is not None:
                raise DuplicateError(
                    f"Năm học '{year_name}' đã tồn tại."
                )
            if is_current:
                self.repository.clear_current_school_years(connection)
            return self.repository.create_school_year(
                connection,
                year_name,
                start_date,
                end_date,
                is_current,
            )

    def update_school_year(
        self,
        school_year_id: int,
        year_name: str,
        start_date: date,
        end_date: date,
        is_current: bool,
    ) -> None:
        self._validate_positive_id("school_year_id", school_year_id)
        year_name = self._validate_school_year_data(
            year_name,
            start_date,
            end_date,
            is_current,
        )
        with self.db.transaction() as connection:
            if self.repository.get_school_year_by_id(
                connection,
                school_year_id,
            ) is None:
                raise ValidationError("Không tìm thấy năm học.")
            duplicate = self.repository.get_school_year_by_name(
                connection,
                year_name,
            )
            if duplicate is not None and duplicate[0] != school_year_id:
                raise DuplicateError(
                    f"Năm học '{year_name}' đã tồn tại."
                )
            if is_current:
                self.repository.clear_current_school_years(connection)
            self.repository.update_school_year(
                connection,
                school_year_id,
                year_name,
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
        status: str = "ACTIVE",
    ) -> int:
        class_name = self._normalize_required_text(
            class_name,
            "Tên lớp",
            30,
        )
        self._validate_positive_id("grade_id", grade_id)
        self._validate_positive_id("school_year_id", school_year_id)
        teacher = self._normalize_optional_text(
            homeroom_teacher,
            "Giáo viên chủ nhiệm",
            100,
        )
        if status not in {"ACTIVE", "INACTIVE"}:
            raise ValidationError("Trạng thái lớp không hợp lệ.")
        with self.db.transaction() as connection:
            self._validate_class_parents(
                connection,
                grade_id,
                school_year_id,
            )
            if self.repository.get_class_by_name_and_year(
                connection,
                class_name,
                school_year_id,
            ) is not None:
                raise DuplicateError(
                    f"Lớp '{class_name}' đã tồn tại trong năm học."
                )
            return self.repository.create_class(
                connection,
                class_name,
                grade_id,
                school_year_id,
                teacher,
                status,
            )

    def get_class(
        self,
        class_id: int,
    ):
        self._validate_positive_id("class_id", class_id)

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
        self._validate_positive_id("school_year_id", school_year_id)

        with self.db.transaction() as connection:
            return self.repository.list_classes_by_school_year(
                connection,
                school_year_id,
            )

    def list_catalog_classes(
        self,
        school_year_id: int,
        grade_id: int | None = None,
    ) -> list[SchoolClass]:
        self._validate_positive_id("school_year_id", school_year_id)
        if grade_id is not None:
            self._validate_positive_id("grade_id", grade_id)
        with self.db.transaction() as connection:
            return self.repository.list_catalog_classes(
                connection,
                school_year_id,
                grade_id,
            )

    def update_class(
        self,
        class_id: int,
        class_name: str,
        grade_id: int,
        school_year_id: int,
        homeroom_teacher: str | None = None,
        status: str = "ACTIVE",
    ) -> None:
        self._validate_positive_id("class_id", class_id)
        self._validate_positive_id("grade_id", grade_id)
        self._validate_positive_id("school_year_id", school_year_id)
        class_name = self._normalize_required_text(
            class_name,
            "Tên lớp",
            30,
        )
        teacher = self._normalize_optional_text(
            homeroom_teacher,
            "Giáo viên chủ nhiệm",
            100,
        )
        if status not in {"ACTIVE", "INACTIVE"}:
            raise ValidationError("Trạng thái lớp không hợp lệ.")

        with self.db.transaction() as connection:
            current = self.repository.get_class_by_id(
                connection,
                class_id,
            )
            if current is None:
                raise ValidationError("Không tìm thấy lớp học.")
            self._validate_class_parents(
                connection,
                grade_id,
                school_year_id,
            )
            if (
                self.repository.class_has_enrollments(connection, class_id)
                and (current[2] != grade_id or current[4] != school_year_id)
            ):
                raise BusinessRuleError(
                    "Không thể đổi năm học hoặc khối của lớp đã có lịch sử."
                )
            duplicate_id = self.repository.get_class_by_name_and_year(
                connection,
                class_name,
                school_year_id,
            )
            if duplicate_id is not None and duplicate_id != class_id:
                raise DuplicateError(
                    f"Lớp '{class_name}' đã tồn tại trong năm học."
                )
            self.repository.update_class(
                connection,
                class_id,
                class_name,
                grade_id,
                school_year_id,
                teacher,
                status,
            )

    def set_class_active(
        self,
        class_id: int,
        is_active: bool,
    ) -> None:
        self._validate_positive_id("class_id", class_id)
        if not isinstance(is_active, bool):
            raise ValidationError("Trạng thái lớp không hợp lệ.")
        with self.db.transaction() as connection:
            current = self.repository.get_class_by_id(
                connection,
                class_id,
            )
            if current is None:
                raise ValidationError("Không tìm thấy lớp học.")
            self.repository.update_class(
                connection,
                current[0],
                current[1],
                current[2],
                current[4],
                current[6],
                "ACTIVE" if is_active else "INACTIVE",
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
        self._validate_positive_id(
            "assessment_id",
            assessment_id,
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

    def list_assessments(
        self,
        school_year_id: int,
        subject_id: int | None = None,
        semester: int | None = None,
        status: AssessmentStatus | None = None,
    ) -> list[Assessment]:
        self._validate_positive_id(
            "school_year_id",
            school_year_id,
        )

        if subject_id is not None:
            self._validate_positive_id(
                "subject_id",
                subject_id,
            )

        if (
            semester is not None
            and (
                isinstance(semester, bool)
                or not isinstance(semester, int)
                or semester not in (1, 2)
            )
        ):
            raise ValidationError(
                "semester chỉ được là 1 hoặc 2."
            )

        if status is not None and not isinstance(
            status,
            AssessmentStatus,
        ):
            raise ValidationError(
                "status assessment không hợp lệ."
            )

        with self.db.transaction() as connection:
            return self.repository.list_assessments(
                connection,
                school_year_id,
                subject_id,
                semester,
                status,
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

    @classmethod
    def _validate_school_year_data(
        cls,
        year_name: str,
        start_date: date,
        end_date: date,
        is_current: bool,
    ) -> str:
        normalized = cls._normalize_required_text(
            year_name,
            "Tên năm học",
            20,
        )
        if not isinstance(start_date, date) or not isinstance(end_date, date):
            raise ValidationError(
                "Ngày bắt đầu và ngày kết thúc không hợp lệ."
            )
        if start_date >= end_date:
            raise ValidationError(
                "Ngày bắt đầu phải nhỏ hơn ngày kết thúc."
            )
        if not isinstance(is_current, bool):
            raise ValidationError("Trạng thái năm học không hợp lệ.")
        return normalized

    @staticmethod
    def _validate_grade_number(grade_number: int) -> None:
        if (
            isinstance(grade_number, bool)
            or not isinstance(grade_number, int)
            or not 6 <= grade_number <= 12
        ):
            raise ValidationError("Khối phải nằm trong khoảng từ 6 đến 12.")

    @staticmethod
    def _normalize_required_text(
        value: str,
        label: str,
        max_length: int,
    ) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValidationError(f"{label} không được để trống.")
        normalized = value.strip()
        if len(normalized) > max_length:
            raise ValidationError(
                f"{label} không được vượt quá {max_length} ký tự."
            )
        return normalized

    @staticmethod
    def _normalize_optional_text(
        value: str | None,
        label: str,
        max_length: int,
    ) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValidationError(f"{label} không hợp lệ.")
        normalized = value.strip()
        if not normalized:
            return None
        if len(normalized) > max_length:
            raise ValidationError(
                f"{label} không được vượt quá {max_length} ký tự."
            )
        return normalized

    def _validate_class_parents(
        self,
        connection,
        grade_id: int,
        school_year_id: int,
    ) -> None:
        if self.repository.get_grade_by_id(connection, grade_id) is None:
            raise ValidationError("Không tìm thấy khối.")
        if self.repository.get_school_year_by_id(
            connection,
            school_year_id,
        ) is None:
            raise ValidationError("Không tìm thấy năm học.")
