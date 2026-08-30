from datetime import date, datetime
from decimal import Decimal

from models.dto import (
    Intervention,
    InterventionDetail,
    InterventionReviewItem,
)
from models.enums import (
    InterventionStatus,
    ReviewResult,
)


def test_create_detected_intervention_without_teacher():
    intervention = Intervention(
        intervention_id=1,
        enrollment_id=1,
        subject_id=1,
        trigger_score_id=10,
        responsible_user_id=None,
        detected_date=date(2026, 9, 7),
        start_date=None,
        status=InterventionStatus.DETECTED,
        support_method=None,
        notes=None,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    assert intervention.status == InterventionStatus.DETECTED
    assert intervention.responsible_user_id is None
    assert intervention.start_date is None


def test_create_review_item():
    review = InterventionReviewItem(
        review_id=1,
        intervention_id=1,
        score_id=20,
        review_date=date(2026, 10, 1),
        result=ReviewResult.NOT_PASSED,
        notes="Tiếp tục bổ trợ.",
        created_at=datetime.now(),
    )

    assert review.result == ReviewResult.NOT_PASSED
    assert review.intervention_id == 1


def test_intervention_detail_contains_reviews():
    review = InterventionReviewItem(
        review_id=1,
        intervention_id=1,
        score_id=20,
        review_date=date(2026, 10, 1),
        result=ReviewResult.PASSED,
        notes=None,
        created_at=datetime.now(),
    )

    detail = InterventionDetail(
        intervention_id=1,
        enrollment_id=1,
        student_id="student-001",
        student_code="HS001",
        full_name="Nguyễn Văn A",
        class_name="10A1",
        subject_id=1,
        subject_name="Toán",
        trigger_score_id=10,
        trigger_score=Decimal("2.80"),
        responsible_user_id=3,
        responsible_user_name="Nguyễn Văn B",
        detected_date=date(2026, 9, 7),
        start_date=date(2026, 9, 10),
        status=InterventionStatus.COMPLETED,
        support_method="Ôn tập theo nhóm",
        notes=None,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        reviews=(review,),
    )

    assert detail.trigger_score == Decimal("2.80")
    assert len(detail.reviews) == 1
    assert detail.reviews[0].result == ReviewResult.PASSED