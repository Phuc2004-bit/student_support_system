from collections.abc import Iterable
from decimal import Decimal
from typing import Protocol

from models.dto.score import Score, ScoreCreateData


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
