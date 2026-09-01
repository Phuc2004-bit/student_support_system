from unittest.mock import Mock, patch

import bootstrap


def test_build_app_context_composes_dashboard_services():
    fake_db = Mock()
    fake_auth = Mock()
    fake_permission = Mock()
    fake_academic = Mock()
    fake_dashboard = Mock()

    with (
        patch.object(
            bootstrap,
            "DatabaseManager",
            return_value=fake_db,
        ),
        patch.object(
            bootstrap,
            "AuthService",
            return_value=fake_auth,
        ),
        patch.object(
            bootstrap,
            "PermissionService",
            return_value=fake_permission,
        ),
        patch.object(
            bootstrap,
            "AcademicService",
            return_value=fake_academic,
        ) as academic_cls,
        patch.object(
            bootstrap,
            "DashboardService",
            return_value=fake_dashboard,
        ) as dashboard_cls,
    ):
        context = bootstrap.build_app_context()

    academic_cls.assert_called_once_with(db=fake_db)
    dashboard_cls.assert_called_once_with(db=fake_db)

    assert context.db is fake_db
    assert context.auth_service is fake_auth
    assert context.permission_service is fake_permission
    assert context.academic_service is fake_academic
    assert context.dashboard_service is fake_dashboard
