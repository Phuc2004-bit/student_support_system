from collections.abc import Iterable
from decimal import Decimal
from typing import Protocol

from models.dto.score import Score, ScoreCreateData, ScoreRosterItem


class ScoreServiceContract(Protocol):
    def create_score(
        self,
        enrollment_id: int,
        assessment_id: int,
        score_value: Decimal,
    ) -> Score:
        ...

    def create_scores(
        self,
        entries: Iterable[ScoreCreateData],
    ) -> list[Score]:
        ...

    def list_score_roster(
        self,
        class_id: int,
        school_year_id: int,
        subject_id: int,
        assessment_id: int,
    ) -> list[ScoreRosterItem]:
        ...
