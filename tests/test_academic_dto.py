from datetime import date, datetime
from decimal import Decimal

from models.dto import (
    Assessment,
    Score,
    SupportRule,
)
from models.enums import AssessmentStatus


def test_create_assessment():
    assessment = Assessment(
        assessment_id=1,
        subject_id=1,
        school_year_id=1,
        assessment_name="Kiểm tra giữa kỳ I",
        semester=1,
        assessment_type="MIDTERM",
        assessment_date=date(2026, 10, 15),
        status=AssessmentStatus.ACTIVE,
        created_at=datetime.now(),
    )

    assert assessment.subject_id == 1
    assert assessment.semester == 1
    assert assessment.status == AssessmentStatus.ACTIVE


def test_score_uses_decimal():
    score = Score(
        score_id=1,
        enrollment_id=1,
        assessment_id=1,
        score=Decimal("3.49"),
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    assert score.score == Decimal("3.49")


def test_support_rule_threshold_uses_decimal():
    rule = SupportRule(
        rule_id=1,
        subject_id=1,
        school_year_id=1,
        threshold=Decimal("3.50"),
        is_active=True,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )

    assert rule.threshold == Decimal("3.50")
    assert rule.is_active is True


def test_boundary_comparison():
    threshold = Decimal("3.50")

    assert Decimal("3.49") < threshold
    assert not Decimal("3.50") < threshold
    assert not Decimal("3.51") < threshold