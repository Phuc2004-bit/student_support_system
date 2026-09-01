from models.dto.dashboard_dto import DashboardData
from services.dashboard_contract import DashboardServiceContract


class FakeDashboardService:
    def get_dashboard(
        self,
        school_year_id: int,
        grade_id: int | None = None,
        class_id: int | None = None,
        subject_id: int | None = None,
    ) -> DashboardData:
        raise NotImplementedError


def test_fake_service_matches_dashboard_contract():
    service: DashboardServiceContract = FakeDashboardService()

    assert hasattr(service, "get_dashboard")
