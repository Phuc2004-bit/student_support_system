from datetime import date
from decimal import Decimal
from typing import Protocol

from models.dto import Intervention


class InterventionPlanningServiceContract(Protocol):
    def plan_intervention(
        self,
        intervention_id: int,
        responsible_user_id: int,
        start_date: date,
        support_method: str | None = None,
        notes: str | None = None,
    ) -> Intervention:
        ...


class InterventionStartServiceContract(Protocol):
    def start_intervention(
        self,
        intervention_id: int,
    ) -> Intervention:
        ...


class InterventionWaitingReviewServiceContract(Protocol):
    def mark_waiting_review(
        self,
        intervention_id: int,
    ) -> Intervention:
        ...


class InterventionContinueServiceContract(Protocol):
    def continue_intervention(
        self,
        intervention_id: int,
    ) -> Intervention:
        ...


class InterventionReviewServiceContract(Protocol):
    def review_intervention(
        self,
        intervention_id: int,
        score_id: int | None = None,
        review_date: date | None = None,
        notes: str | None = None,
        *,
        assessment_id: int | None = None,
        score_value: Decimal | str | None = None,
    ) -> Intervention:
        ...
