from collections.abc import Iterable
from decimal import Decimal

from database.connection import DatabaseManager
from exceptions import (
    DuplicateError,
    ValidationError,
)
from models.dto import Score, ScoreCreateData
from repositories import (
    AcademicRepository,
    EnrollmentRepository,
    InterventionRepository,
    ScoreRepository,
    SupportRuleRepository,
)
from services.support_service import SupportService


class ScoreService:
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
        self._validate_create_data(entry)

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

        for entry in batch:
            self._validate_create_data(entry)

        with self.db.transaction() as connection:
            return [
                self._create_score(connection, entry)
                for entry in batch
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

        return self.score_repository.create(
            connection,
            entry.enrollment_id,
            entry.assessment_id,
            entry.score_value,
        )

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

        if enrollment_id <= 0:
            raise ValidationError(
                "enrollment_id không hợp lệ."
            )

        if assessment_id <= 0:
            raise ValidationError(
                "assessment_id không hợp lệ."
            )

        self._validate_score_value(score_value)

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
        if score_id <= 0:
            raise ValidationError(
                "score_id không hợp lệ."
            )

        self._validate_score_value(score_value)

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

    # =====================================================
    # VALIDATION
    # =====================================================

    @staticmethod
    def _validate_create_data(
        entry: ScoreCreateData,
    ) -> None:
        if not isinstance(entry, ScoreCreateData):
            raise ValidationError(
                "Dữ liệu điểm không hợp lệ."
            )

        for field_name, value in (
            ("enrollment_id", entry.enrollment_id),
            ("assessment_id", entry.assessment_id),
        ):
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value <= 0
            ):
                raise ValidationError(
                    f"{field_name} không hợp lệ."
                )

        ScoreService._validate_score_value(entry.score_value)

    @staticmethod
    def _validate_score_value(
        score_value: Decimal,
    ) -> None:
        if score_value is None:
            raise ValidationError(
                "Điểm không được để trống."
            )

        if score_value < Decimal("0"):
            raise ValidationError(
                "Điểm không được nhỏ hơn 0."
            )

        if score_value > Decimal("10"):
            raise ValidationError(
                "Điểm không được lớn hơn 10."
            )
