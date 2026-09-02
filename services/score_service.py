from collections.abc import Iterable
from decimal import Decimal, InvalidOperation

import pyodbc

from database.connection import DatabaseManager
from exceptions import (
    BusinessRuleError,
    DuplicateError,
    ValidationError,
)
from models.dto import Score, ScoreCreateData, ScoreRosterItem
from models.enums import EnrollmentStatus
from repositories import (
    AcademicRepository,
    EnrollmentRepository,
    InterventionRepository,
    ScoreRepository,
    SupportRuleRepository,
)
from services.support_service import SupportService


class ScoreService:
    MIN_SCORE = Decimal("0")
    MAX_SCORE = Decimal("10")
    SCORE_QUANTUM = Decimal("0.01")

    def __init__(
        self,
        db: DatabaseManager,
        score_repository: ScoreRepository | None = None,
        enrollment_repository: EnrollmentRepository | None = None,
        academic_repository: AcademicRepository | None = None,
        rule_repository: SupportRuleRepository | None = None,
        intervention_repository: InterventionRepository | None = None,
    ):
        self.db = db

        self.score_repository = (
            score_repository
            or ScoreRepository()
        )

        self.enrollment_repository = (
            enrollment_repository
            or EnrollmentRepository()
        )

        self.academic_repository = (
            academic_repository
            or AcademicRepository()
        )

        self.rule_repository = (
            rule_repository
            or SupportRuleRepository()
        )

        self.intervention_repository = (
            intervention_repository
            or InterventionRepository()
        )

    # =====================================================
    # CREATE
    # =====================================================

    def create_score(
        self,
        enrollment_id: int,
        assessment_id: int,
        score_value: Decimal,
    ) -> Score:
        """
        Tạo một điểm thông thường.

        Method này chỉ lưu SCORES,
        KHÔNG tự động phát hiện bổ trợ.

        Sau này UI nhập điểm chính thức nên ưu tiên dùng
        create_score_and_detect().
        """

        entry = ScoreCreateData(
            enrollment_id=enrollment_id,
            assessment_id=assessment_id,
            score_value=score_value,
        )
        entry = self._normalize_create_data(entry)

        with self.db.transaction() as connection:
            return self._create_score(connection, entry)

    def create_scores(
        self,
        entries: Iterable[ScoreCreateData],
    ) -> list[Score]:
        try:
            batch = tuple(entries)
        except TypeError as exc:
            raise ValidationError(
                "Danh sách điểm không hợp lệ."
            ) from exc

        if not batch:
            raise ValidationError(
                "Danh sách điểm không được để trống."
            )

        normalized: list[ScoreCreateData] = []
        seen_keys: set[tuple[int, int]] = set()
        for entry in batch:
            normalized_entry = self._normalize_create_data(entry)
            key = (
                normalized_entry.enrollment_id,
                normalized_entry.assessment_id,
            )
            if key in seen_keys:
                raise DuplicateError(
                    "Batch có enrollment và bài đánh giá bị trùng."
                )
            seen_keys.add(key)
            normalized.append(normalized_entry)

        with self.db.transaction() as connection:
            return [
                self._create_score(connection, entry)
                for entry in normalized
            ]

    def _create_score(
        self,
        connection,
        entry: ScoreCreateData,
    ) -> Score:
        enrollment = self.enrollment_repository.get_by_id(
            connection,
            entry.enrollment_id,
        )
        if enrollment is None:
            raise ValidationError(
                "Không tìm thấy enrollment."
            )

        assessment = self.academic_repository.get_assessment_by_id(
            connection,
            entry.assessment_id,
        )
        if assessment is None:
            raise ValidationError(
                "Không tìm thấy bài đánh giá."
            )

        existing = (
            self.score_repository.get_by_enrollment_assessment(
                connection,
                entry.enrollment_id,
                entry.assessment_id,
            )
        )
        if existing is not None:
            raise DuplicateError(
                "Học sinh đã có điểm cho bài đánh giá này."
            )

        try:
            return self.score_repository.create(
                connection,
                entry.enrollment_id,
                entry.assessment_id,
                entry.score_value,
            )
        except pyodbc.IntegrityError as exc:
            if self._is_duplicate_database_error(exc):
                raise DuplicateError(
                    "Học sinh đã có điểm cho bài đánh giá này."
                ) from exc
            raise

    def create_score_and_detect(
        self,
        enrollment_id: int,
        assessment_id: int,
        score_value: Decimal,
    ):
        """
        Lưu điểm và phát hiện học sinh cần bổ trợ
        trong CÙNG MỘT transaction.

        Nếu score < threshold:
            → tạo DETECTED nếu chưa có intervention mở.

        Nếu score >= threshold:
            → chỉ lưu score.

        Nếu quá trình detection phát sinh lỗi:
            → rollback cả score vừa tạo.

        Returns:
            tuple[Score, Intervention | None]
        """

        self._validate_identifier("enrollment_id", enrollment_id)
        self._validate_identifier("assessment_id", assessment_id)
        score_value = self._normalize_score_value(score_value)

        with self.db.transaction() as connection:

            # =================================================
            # 1. KIỂM TRA ENROLLMENT
            # =================================================

            enrollment = (
                self.enrollment_repository.get_by_id(
                    connection,
                    enrollment_id,
                )
            )

            if enrollment is None:
                raise ValidationError(
                    "Không tìm thấy enrollment."
                )

            # =================================================
            # 2. KIỂM TRA ASSESSMENT
            # =================================================

            assessment = (
                self.academic_repository
                .get_assessment_by_id(
                    connection,
                    assessment_id,
                )
            )

            if assessment is None:
                raise ValidationError(
                    "Không tìm thấy bài đánh giá."
                )

            # =================================================
            # 3. KIỂM TRA DUPLICATE SCORE
            # =================================================

            existing = (
                self.score_repository
                .get_by_enrollment_assessment(
                    connection,
                    enrollment_id,
                    assessment_id,
                )
            )

            if existing is not None:
                raise DuplicateError(
                    "Học sinh đã có điểm cho bài đánh giá này."
                )

            # =================================================
            # 4. LƯU SCORE
            # =================================================

            score = self.score_repository.create(
                connection,
                enrollment_id,
                assessment_id,
                score_value,
            )

            # =================================================
            # 5. PHÁT HIỆN BỔ TRỢ
            #
            # Quan trọng:
            # KHÔNG gọi detect_from_score()
            # vì method đó tự mở transaction.
            #
            # Ta gọi _detect_from_score() để sử dụng
            # chính connection hiện tại.
            # =================================================

            support_service = SupportService(
                db=self.db,
                score_repository=self.score_repository,
                academic_repository=self.academic_repository,
                rule_repository=self.rule_repository,
                intervention_repository=self.intervention_repository,
            )

            intervention = (
                support_service._detect_from_score(
                    connection,
                    score.score_id,
                )
            )

            # Chỉ khi cả INSERT SCORE và DETECTION đều thành công
            # thì context manager mới COMMIT.
            #
            # Nếu detection raise exception:
            # DatabaseManager sẽ ROLLBACK toàn bộ transaction.

            return score, intervention

    # =====================================================
    # READ
    # =====================================================

    def list_score_roster(
        self,
        class_id: int,
        school_year_id: int,
        subject_id: int,
        assessment_id: int,
    ) -> list[ScoreRosterItem]:
        for field_name, value in (
            ("class_id", class_id),
            ("school_year_id", school_year_id),
            ("subject_id", subject_id),
            ("assessment_id", assessment_id),
        ):
            self._validate_identifier(field_name, value)

        with self.db.transaction() as connection:
            assessment = self.academic_repository.get_assessment_by_id(
                connection,
                assessment_id,
            )
            if assessment is None:
                raise ValidationError(
                    "Không tìm thấy bài đánh giá."
                )
            if (
                assessment.school_year_id != school_year_id
                or assessment.subject_id != subject_id
            ):
                raise ValidationError(
                    "Bài đánh giá không thuộc năm học và môn đã chọn."
                )

            return self.score_repository.list_by_class_assessment(
                connection,
                class_id,
                school_year_id,
                assessment_id,
                EnrollmentStatus.ACTIVE,
            )

    def get_score(
        self,
        score_id: int,
    ) -> Score:
        if score_id <= 0:
            raise ValidationError(
                "score_id không hợp lệ."
            )

        with self.db.transaction() as connection:

            score = self.score_repository.get_by_id(
                connection,
                score_id,
            )

            if score is None:
                raise ValidationError(
                    "Không tìm thấy điểm."
                )

            return score

    def list_scores_by_enrollment(
        self,
        enrollment_id: int,
    ) -> list[Score]:
        if enrollment_id <= 0:
            raise ValidationError(
                "enrollment_id không hợp lệ."
            )

        with self.db.transaction() as connection:

            return (
                self.score_repository
                .list_by_enrollment(
                    connection,
                    enrollment_id,
                )
            )

    # =====================================================
    # UPDATE
    # =====================================================

    def update_score(
        self,
        score_id: int,
        score_value: Decimal,
    ) -> Score:
        self._validate_identifier("score_id", score_id)
        score_value = self._normalize_score_value(score_value)

        with self.db.transaction() as connection:

            existing = (
                self.score_repository.get_by_id(
                    connection,
                    score_id,
                )
            )

            if existing is None:
                raise ValidationError(
                    "Không tìm thấy điểm cần cập nhật."
                )

            if self.intervention_repository.is_score_linked_to_support(
                connection,
                score_id,
            ):
                raise BusinessRuleError(
                    "Không thể sửa điểm đã được sử dụng trong lịch sử bổ trợ."
                )

            updated = self.score_repository.update(
                connection,
                score_id,
                score_value,
            )

            if updated is None:
                raise ValidationError(
                    "Không thể cập nhật điểm."
                )

            return updated

    def can_edit_score(self, score_id: int) -> bool:
        self._validate_identifier("score_id", score_id)

        with self.db.transaction() as connection:
            existing = self.score_repository.get_by_id(
                connection,
                score_id,
            )
            if existing is None:
                raise ValidationError(
                    "Không tìm thấy điểm cần cập nhật."
                )
            return not self.intervention_repository.is_score_linked_to_support(
                connection,
                score_id,
            )

    # =====================================================
    # VALIDATION
    # =====================================================

    @staticmethod
    def _normalize_create_data(
        entry: ScoreCreateData,
    ) -> ScoreCreateData:
        if not isinstance(entry, ScoreCreateData):
            raise ValidationError(
                "Dữ liệu điểm không hợp lệ."
            )

        for field_name, value in (
            ("enrollment_id", entry.enrollment_id),
            ("assessment_id", entry.assessment_id),
        ):
            ScoreService._validate_identifier(field_name, value)

        return ScoreCreateData(
            enrollment_id=entry.enrollment_id,
            assessment_id=entry.assessment_id,
            score_value=ScoreService._normalize_score_value(
                entry.score_value
            ),
        )

    @staticmethod
    def _validate_identifier(
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
    def _normalize_score_value(cls, score_value) -> Decimal:
        if score_value is None or isinstance(score_value, bool):
            raise ValidationError(
                "Điểm không hợp lệ."
            )

        if isinstance(score_value, str):
            score_text = score_value.strip()
            if not score_text:
                raise ValidationError(
                    "Điểm không được để trống."
                )
        elif isinstance(score_value, (Decimal, int, float)):
            score_text = str(score_value)
        else:
            raise ValidationError(
                "Kiểu dữ liệu điểm không hợp lệ."
            )

        try:
            normalized = Decimal(score_text)
        except (InvalidOperation, ValueError):
            raise ValidationError(
                "Điểm phải là một giá trị số hợp lệ."
            ) from None

        if not normalized.is_finite():
            raise ValidationError(
                "Điểm phải là một số hữu hạn."
            )

        if normalized < cls.MIN_SCORE or normalized > cls.MAX_SCORE:
            raise ValidationError(
                "Điểm phải nằm trong khoảng từ 0 đến 10."
            )

        try:
            rounded = normalized.quantize(cls.SCORE_QUANTUM)
        except InvalidOperation:
            raise ValidationError(
                "Độ chính xác của điểm không hợp lệ."
            ) from None

        if rounded != normalized:
            raise ValidationError(
                "Điểm chỉ được có tối đa 2 chữ số thập phân."
            )

        return normalized

    @classmethod
    def _validate_score_value(cls, score_value) -> None:
        cls._normalize_score_value(score_value)

    @staticmethod
    def _is_duplicate_database_error(exc: Exception) -> bool:
        message = str(exc).upper()
        return any(
            marker in message
            for marker in ("2601", "2627", "UNIQUE")
        )
