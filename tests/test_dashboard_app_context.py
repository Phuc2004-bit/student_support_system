from unittest.mock import Mock

from app_context import AppContext


def test_app_context_keeps_dashboard_dependencies_optional():
    context = AppContext(
        db=Mock(),
        auth_service=Mock(),
        permission_service=Mock(),
    )

    assert context.academic_service is None
    assert context.dashboard_service is None


def test_app_context_accepts_dashboard_dependencies():
    academic_service = Mock()
    dashboard_service = Mock()

    context = AppContext(
        db=Mock(),
        auth_service=Mock(),
        permission_service=Mock(),
        academic_service=academic_service,
        dashboard_service=dashboard_service,
    )

    assert context.academic_service is academic_service
    assert context.dashboard_service is dashboard_service
