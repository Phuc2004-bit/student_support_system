from dataclasses import replace
from datetime import date

from database.connection import DatabaseManager
from exceptions import (
    InvalidStateTransitionError,
    MissingSupportRuleError,
    ValidationError,
)
from models.dto import Intervention, InterventionDetail
from models.enums import (
    InterventionStatus,
    ReviewResult,
)
from repositories import (
    AcademicRepository,
    InterventionRepository,
    ScoreRepository,
    SupportRuleRepository,
)


class SupportService:
    # =====================================================
    # STATE MACHINE
    # =====================================================

    ALLOWED_TRANSITIONS = {
        InterventionStatus.DETECTED: {
            InterventionStatus.PLANNED,
        },
        InterventionStatus.PLANNED: {
            InterventionStatus.IN_PROGRESS,
        },
        InterventionStatus.IN_PROGRESS: {
            InterventionStatus.WAITING_REVIEW,
        },
        InterventionStatus.WAITING_REVIEW: {
            InterventionStatus.CONTINUE,
            InterventionStatus.COMPLETED,
        },
        InterventionStatus.CONTINUE: {
            InterventionStatus.IN_PROGRESS,
        },
        InterventionStatus.COMPLETED: set(),
    }

    def __init__(
        self,
        db: DatabaseManager,
        score_repository: ScoreRepository | None = None,
        academic_repository: AcademicRepository | None = None,
        rule_repository: SupportRuleRepository | None = None,
        intervention_repository: InterventionRepository | None = None,
    ):
        self.db = db

        self.score_repository = (
            score_repository
            or ScoreRepository()
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
    # INTERNAL TRANSITION
    # =====================================================

    def _transition(
        self,
        connection,
        intervention_id: int,
        target_status: InterventionStatus,
        required_source_status: InterventionStatus | None = None,
    ) -> Intervention:
        intervention = (
            self.intervention_repository.get_by_id(
                connection,
                intervention_id,
            )
        )

        if intervention is None:
            raise ValidationError(
                "Không tìm thấy hồ sơ bổ trợ."
            )

        if (
            required_source_status is not None
            and intervention.status != required_source_status
        ):
            raise InvalidStateTransitionError(
                f"Không thể chuyển trạng thái "
                f"{intervention.status.value} "
                f"→ {target_status.value}."
            )

        allowed = self.ALLOWED_TRANSITIONS.get(
            intervention.status,
            set(),
        )

        if target_status not in allowed:
            raise InvalidStateTransitionError(
                f"Không thể chuyển trạng thái "
                f"{intervention.status.value} "
                f"→ {target_status.value}."
            )

        updated = (
            self.intervention_repository.update_status(
                connection,
                intervention_id,
                target_status,
            )
        )

        if updated is None:
            raise ValidationError(
                "Không thể cập nhật trạng thái hồ sơ bổ trợ."
            )

        return updated

    # =====================================================
    # DETECTION
    # =====================================================

    def _detect_from_score(
        self,
        connection,
        score_id: int,
        detected_date: date | None = None,
    ) -> Intervention | None:
        """
        Phát hiện học sinh cần bổ trợ bằng connection hiện có.

        Method nội bộ này KHÔNG:
        - mở transaction
        - commit
        - rollback

        Transaction thuộc về Service gọi nó.
        """

        if score_id <= 0:
            raise ValidationError(
                "score_id không hợp lệ."
            )

        # =============================================
        # 1. SCORE
        # =============================================
        score = self.score_repository.get_by_id(
            connection,
            score_id,
        )

        if score is None:
            raise ValidationError(
                "Không tìm thấy điểm."
            )

        # =============================================
        # 2. ASSESSMENT
        # =============================================
        assessment = (
            self.academic_repository
            .get_assessment_by_id(
                connection,
                score.assessment_id,
            )
        )

        if assessment is None:
            raise ValidationError(
                "Không tìm thấy bài đánh giá."
            )

        # =============================================
        # 3. SUPPORT RULE
        # =============================================
        rule = self.rule_repository.get_active_rule(
            connection,
            assessment.subject_id,
            assessment.school_year_id,
        )

        if rule is None:
            raise MissingSupportRuleError(
                "Không tìm thấy quy tắc bổ trợ "
                "đang hoạt động cho môn học "
                "và năm học này."
            )

        # =============================================
        # 4. SO SÁNH NGƯỠNG
        # =============================================
        if score.score >= rule.threshold:
            return None

        # =============================================
        # 5. OPEN INTERVENTION
        # =============================================
        existing = (
            self.intervention_repository.get_open(
                connection,
                score.enrollment_id,
                assessment.subject_id,
            )
        )

        if existing is not None:
            return existing

        # =============================================
        # 6. CREATE DETECTED
        # =============================================
        effective_date = (
            detected_date
            or assessment.assessment_date
            or date.today()
        )

        return self.intervention_repository.create(
            connection,
            score.enrollment_id,
            assessment.subject_id,
            score.score_id,
            effective_date,
        )

    def detect_from_score(
        self,
        score_id: int,
        detected_date: date | None = None,
    ) -> Intervention | None:
        """
        Public API dùng khi cần phát hiện từ một score đã tồn tại.
        """

        with self.db.transaction() as connection:
            return self._detect_from_score(
                connection,
                score_id,
                detected_date,
            )

    # =====================================================
    # DETECTED -> PLANNED
    # =====================================================

    def plan_intervention(
        self,
        intervention_id: int,
        responsible_user_id: int,
        start_date: date,
        support_method: str | None = None,
        notes: str | None = None,
    ) -> Intervention:
        if intervention_id <= 0:
            raise ValidationError(
                "intervention_id không hợp lệ."
            )

        if responsible_user_id <= 0:
            raise ValidationError(
                "responsible_user_id không hợp lệ."
            )

        if start_date is None:
            raise ValidationError(
                "Ngày bắt đầu không được để trống."
            )

        with self.db.transaction() as connection:
            intervention = (
                self.intervention_repository.get_by_id(
                    connection,
                    intervention_id,
                )
            )

            if intervention is None:
                raise ValidationError(
                    "Không tìm thấy hồ sơ bổ trợ."
                )

            if (
                intervention.status
                != InterventionStatus.DETECTED
            ):
                raise InvalidStateTransitionError(
                    "Chỉ hồ sơ DETECTED "
                    "mới được lập kế hoạch."
                )

            planned = (
                self.intervention_repository.update_plan(
                    connection,
                    intervention_id,
                    responsible_user_id,
                    start_date,
                    support_method,
                    notes,
                )
            )

            if planned is None:
                raise ValidationError(
                    "Không thể lưu kế hoạch bổ trợ."
                )

            return self._transition(
                connection,
                intervention_id,
                InterventionStatus.PLANNED,
            )

    # =====================================================
    # PLANNED -> IN_PROGRESS
    # =====================================================

    def start_intervention(
        self,
        intervention_id: int,
    ) -> Intervention:
        if intervention_id <= 0:
            raise ValidationError(
                "intervention_id không hợp lệ."
            )

        with self.db.transaction() as connection:
            return self._transition(
                connection,
                intervention_id,
                InterventionStatus.IN_PROGRESS,
                required_source_status=InterventionStatus.PLANNED,
            )

    # =====================================================
    # IN_PROGRESS -> WAITING_REVIEW
    # =====================================================

    def mark_waiting_review(
        self,
        intervention_id: int,
    ) -> Intervention:
        if intervention_id <= 0:
            raise ValidationError(
                "intervention_id không hợp lệ."
            )

        with self.db.transaction() as connection:
            return self._transition(
                connection,
                intervention_id,
                InterventionStatus.WAITING_REVIEW,
                required_source_status=InterventionStatus.IN_PROGRESS,
            )

    # =====================================================
    # CONTINUE -> IN_PROGRESS
    # =====================================================

    def continue_intervention(
        self,
        intervention_id: int,
    ) -> Intervention:
        if intervention_id <= 0:
            raise ValidationError(
                "intervention_id không hợp lệ."
            )

        with self.db.transaction() as connection:
            return self._transition(
                connection,
                intervention_id,
                InterventionStatus.IN_PROGRESS,
            )

    # =====================================================
    # READ
    # =====================================================

    def get_intervention(
        self,
        intervention_id: int,
    ) -> Intervention:
        if intervention_id <= 0:
            raise ValidationError(
                "intervention_id không hợp lệ."
            )

        with self.db.transaction() as connection:
            intervention = (
                self.intervention_repository.get_by_id(
                    connection,
                    intervention_id,
                )
            )

            if intervention is None:
                raise ValidationError(
                    "Không tìm thấy hồ sơ bổ trợ."
                )

            return intervention

    def get_intervention_detail(
        self,
        intervention_id: int,
    ) -> InterventionDetail:
        if (
            isinstance(intervention_id, bool)
            or not isinstance(intervention_id, int)
            or intervention_id <= 0
        ):
            raise ValidationError(
                "intervention_id không hợp lệ."
            )

        with self.db.transaction() as connection:
            detail = self.intervention_repository.get_detail(
                connection,
                intervention_id,
            )
            if detail is None:
                raise ValidationError(
                    "Không tìm thấy hồ sơ bổ trợ."
                )

            reviews = self.intervention_repository.list_reviews(
                connection,
                intervention_id,
            )
            return replace(detail, reviews=tuple(reviews))

    def get_open_intervention(
        self,
        enrollment_id: int,
        subject_id: int,
    ) -> Intervention | None:
        if enrollment_id <= 0:
            raise ValidationError(
                "enrollment_id không hợp lệ."
            )

        if subject_id <= 0:
            raise ValidationError(
                "subject_id không hợp lệ."
            )

        with self.db.transaction() as connection:
            return (
                self.intervention_repository.get_open(
                    connection,
                    enrollment_id,
                    subject_id,
                )
            )
    # =====================================================
    # REVIEW INTERVENTION
    # WAITING_REVIEW -> CONTINUE / COMPLETED
    # =====================================================

    def review_intervention(
        self,
        intervention_id: int,
        score_id: int,
        review_date: date,
        notes: str | None = None,
    ) -> Intervention:
        if intervention_id <= 0:
            raise ValidationError(
                "intervention_id không hợp lệ."
            )

        if score_id <= 0:
            raise ValidationError(
                "score_id không hợp lệ."
            )

        if review_date is None:
            raise ValidationError(
                "Ngày đánh giá lại không được để trống."
            )

        with self.db.transaction() as connection:
            intervention = (
                self.intervention_repository.get_by_id(
                    connection,
                    intervention_id,
                )
            )

            if intervention is None:
                raise ValidationError(
                    "Không tìm thấy hồ sơ bổ trợ."
                )

            if (
                intervention.status
                != InterventionStatus.WAITING_REVIEW
            ):
                raise InvalidStateTransitionError(
                    "Chỉ hồ sơ WAITING_REVIEW "
                    "mới được đánh giá lại."
                )

            score = self.score_repository.get_by_id(
                connection,
                score_id,
            )

            if score is None:
                raise ValidationError(
                    "Không tìm thấy điểm đánh giá lại."
                )

            if (
                score.enrollment_id
                != intervention.enrollment_id
            ):
                raise ValidationError(
                    "Điểm đánh giá lại không thuộc "
                    "đúng học sinh của hồ sơ bổ trợ."
                )

            assessment = (
                self.academic_repository
                .get_assessment_by_id(
                    connection,
                    score.assessment_id,
                )
            )

            if assessment is None:
                raise ValidationError(
                    "Không tìm thấy bài đánh giá lại."
                )

            if (
                assessment.subject_id
                != intervention.subject_id
            ):
                raise ValidationError(
                    "Điểm đánh giá lại không thuộc "
                    "đúng môn của hồ sơ bổ trợ."
                )

            rule = self.rule_repository.get_active_rule(
                connection,
                assessment.subject_id,
                assessment.school_year_id,
            )

            if rule is None:
                raise MissingSupportRuleError(
                    "Không tìm thấy quy tắc bổ trợ "
                    "đang hoạt động."
                )

            if score.score >= rule.threshold:
                result = ReviewResult.PASSED
                target_status = (
                    InterventionStatus.COMPLETED
                )
            else:
                result = ReviewResult.NOT_PASSED
                target_status = (
                    InterventionStatus.CONTINUE
                )

            self.intervention_repository.create_review(
                connection,
                intervention_id,
                score_id,
                review_date,
                result,
                notes,
            )

            return self._transition(
                connection,
                intervention_id,
                target_status,
            )

