from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal

import pytest

from exceptions import MissingSupportRuleError
from models.dto import (
    Assessment,
    Intervention,
    Score,
    ScoreBatchDetectionResult,
    ScoreCreateData,
    SupportRule,
)
from models.enums import AssessmentStatus, InterventionStatus
from services.score_service import ScoreService


NOW = datetime(2026, 9, 2)


class AtomicDb:
    def __init__(self):
        self.connection = object()
        self.transactions = 0
        self.commits = 0
        self.rollbacks = 0
        self.resources = []

    @contextmanager
    def transaction(self):
        self.transactions += 1
        snapshots = [resource.snapshot() for resource in self.resources]
        try:
            yield self.connection
        except Exception:
            for resource, snapshot in zip(self.resources, snapshots):
                resource.restore(snapshot)
            self.rollbacks += 1
            raise
        else:
            self.commits += 1


class ScoreRepo:
    def __init__(self):
        self.items = []
        self.commit_calls = 0

    def snapshot(self):
        return list(self.items)

    def restore(self, snapshot):
        self.items = snapshot

    def get_by_id(self, _connection, score_id):
        return next((x for x in self.items if x.score_id == score_id), None)

    def get_by_enrollment_assessment(
        self, _connection, enrollment_id, assessment_id
    ):
        return next(
            (x for x in self.items
             if x.enrollment_id == enrollment_id
             and x.assessment_id == assessment_id),
            None,
        )

    def create(self, _connection, enrollment_id, assessment_id, value):
        score = Score(
            len(self.items) + 1, enrollment_id, assessment_id,
            value, NOW, NOW,
        )
        self.items.append(score)
        return score


class EnrollmentRepo:
    def get_by_id(self, _connection, enrollment_id):
        return object() if enrollment_id > 0 else None


class AcademicRepo:
    def __init__(self):
        self.items = {
            assessment_id: Assessment(
                assessment_id, 11, 2, f"A{assessment_id}", 1,
                "TEST", date(2026, 10, assessment_id - 99),
                AssessmentStatus.ACTIVE, NOW,
            )
            for assessment_id in range(101, 106)
        }

    def get_assessment_by_id(self, _connection, assessment_id):
        return self.items.get(assessment_id)


class RuleRepo:
    def __init__(self, threshold=Decimal("3.50"), fail_on_call=None):
        self.threshold = threshold
        self.fail_on_call = fail_on_call
        self.calls = []

    def get_active_rule(self, connection, subject_id, school_year_id):
        self.calls.append((connection, subject_id, school_year_id))
        if self.fail_on_call == len(self.calls):
            raise RuntimeError("detection failed")
        if self.threshold is None:
            return None
        return SupportRule(
            1, subject_id, school_year_id, self.threshold, True, NOW, NOW
        )


class InterventionRepo:
    def __init__(self):
        self.items = []
        self.commit_calls = 0

    def snapshot(self):
        return list(self.items)

    def restore(self, snapshot):
        self.items = snapshot

    def get_open(self, _connection, enrollment_id, subject_id):
        return next(
            (x for x in reversed(self.items)
             if x.enrollment_id == enrollment_id
             and x.subject_id == subject_id
             and x.status != InterventionStatus.COMPLETED),
            None,
        )

    def create(
        self, _connection, enrollment_id, subject_id, trigger_score_id,
        detected_date, responsible_user_id=None,
    ):
        item = Intervention(
            len(self.items) + 1, enrollment_id, subject_id,
            trigger_score_id, responsible_user_id, detected_date, None,
            InterventionStatus.DETECTED, None, None, NOW, NOW,
        )
        self.items.append(item)
        return item


def make_service(threshold=Decimal("3.50"), fail_on_call=None):
    db = AtomicDb()
    scores = ScoreRepo()
    rules = RuleRepo(threshold, fail_on_call)
    interventions = InterventionRepo()
    db.resources = [scores, interventions]
    service = ScoreService(
        db,
        score_repository=scores,
        enrollment_repository=EnrollmentRepo(),
        academic_repository=AcademicRepo(),
        rule_repository=rules,
        intervention_repository=interventions,
    )
    return service, db, scores, rules, interventions


def entry(enrollment_id, assessment_id, value):
    return ScoreCreateData(enrollment_id, assessment_id, Decimal(value))


def test_mixed_batch_detects_only_scores_below_rule_threshold():
    service, db, scores, rules, interventions = make_service()

    result = service.create_scores_and_detect((
        entry(1, 101, "3.49"),
        entry(2, 101, "3.50"),
        entry(3, 101, "3.51"),
    ))

    assert isinstance(result, ScoreBatchDetectionResult)
    assert [x.score for x in result.scores] == [
        Decimal("3.49"), Decimal("3.50"), Decimal("3.51")
    ]
    assert result.detected_intervention_count == 1
    assert result.interventions[0].status == InterventionStatus.DETECTED
    assert result.interventions[0].trigger_score_id == result.scores[0].score_id
    assert rules.calls == [(db.connection, 11, 2)] * 3
    assert len(scores.items) == 3
    assert len(interventions.items) == 1
    assert db.transactions == 1
    assert db.commits == 1


@pytest.mark.parametrize(
    "threshold,value,detected",
    [("7.00", "6.99", 1), ("2.00", "3.49", 0)],
)
def test_detection_behavior_follows_configured_rule(
    threshold, value, detected
):
    service, _db, _scores, _rules, _interventions = make_service(
        Decimal(threshold)
    )
    result = service.create_scores_and_detect((entry(1, 101, value),))
    assert result.detected_intervention_count == detected


def test_missing_active_rule_rolls_back_whole_batch():
    service, db, scores, _rules, interventions = make_service(None)

    with pytest.raises(MissingSupportRuleError):
        service.create_scores_and_detect((
            entry(1, 101, "8"), entry(2, 101, "2")
        ))

    assert scores.items == []
    assert interventions.items == []
    assert db.rollbacks == 1
    assert db.commits == 0


def test_late_detection_failure_rolls_back_scores_and_earlier_intervention():
    service, db, scores, _rules, interventions = make_service(
        fail_on_call=2
    )

    with pytest.raises(RuntimeError, match="detection failed"):
        service.create_scores_and_detect((
            entry(1, 101, "2"), entry(2, 101, "2.5")
        ))

    assert scores.items == []
    assert interventions.items == []
    assert db.rollbacks == 1


def test_second_low_score_reuses_open_intervention_without_duplicate():
    service, _db, _scores, _rules, interventions = make_service()

    result = service.create_scores_and_detect((
        entry(1, 101, "2"), entry(1, 102, "2.5")
    ))

    assert len(result.scores) == 2
    assert result.detected_intervention_count == 1
    assert len(interventions.items) == 1


def test_completed_episode_allows_new_detected_intervention():
    service, _db, _scores, _rules, interventions = make_service()
    first = service.create_scores_and_detect((entry(1, 101, "2"),))
    interventions.items[0] = Intervention(
        **{
            field: getattr(interventions.items[0], field)
            for field in interventions.items[0].__dataclass_fields__
            if field != "status"
        },
        status=InterventionStatus.COMPLETED,
    )

    second = service.create_scores_and_detect((entry(1, 102, "2.5"),))

    assert first.interventions[0].intervention_id == 1
    assert second.interventions[0].intervention_id == 2
    assert len(interventions.items) == 2


def test_batch_repositories_never_commit():
    service, _db, scores, _rules, interventions = make_service()
    service.create_scores_and_detect((entry(1, 101, "2"),))
    assert scores.commit_calls == 0
    assert interventions.commit_calls == 0
