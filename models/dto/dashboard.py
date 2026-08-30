from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DashboardSummary:
    total_students: int
    need_support: int
    in_progress: int
    waiting_review: int
    completed: int
    continue_count: int