from __future__ import annotations

from typing import Protocol

from models.dto.dashboard_dto import DashboardData


class DashboardServiceContract(Protocol):
    """
    Contract mà DashboardPage sẽ sử dụng.

    UI chỉ cần biết method này, không cần biết repository hay SQL.
    """

    def get_dashboard(
        self,
        school_year_id: int,
        grade_id: int | None = None,
        class_id: int | None = None,
        subject_id: int | None = None,
    ) -> DashboardData:
        ...
