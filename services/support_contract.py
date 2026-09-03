from datetime import date
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
