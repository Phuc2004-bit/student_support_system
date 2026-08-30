from models.enums import (
    InterventionStatus,
    ReviewResult,
    UserRole,
)


def test_user_roles():
    assert UserRole.ADMIN.value == "ADMIN"
    assert UserRole.TEACHER.value == "TEACHER"


def test_intervention_statuses():
    assert InterventionStatus.DETECTED.value == "DETECTED"
    assert InterventionStatus.PLANNED.value == "PLANNED"
    assert InterventionStatus.IN_PROGRESS.value == "IN_PROGRESS"
    assert InterventionStatus.WAITING_REVIEW.value == "WAITING_REVIEW"
    assert InterventionStatus.CONTINUE.value == "CONTINUE"
    assert InterventionStatus.COMPLETED.value == "COMPLETED"


def test_review_results():
    assert ReviewResult.PASSED.value == "PASSED"
    assert ReviewResult.NOT_PASSED.value == "NOT_PASSED"