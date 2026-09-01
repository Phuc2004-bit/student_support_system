from app_context import AppContext
from bootstrap import build_app_context
from database.connection import DatabaseManager
from services.auth_service import AuthService
from services.permission_service import PermissionService


def test_build_app_context_creates_core_dependencies():
    context = build_app_context()

    assert isinstance(context, AppContext)
    assert isinstance(context.db, DatabaseManager)
    assert isinstance(context.auth_service, AuthService)
    assert isinstance(
        context.permission_service,
        PermissionService,
    )


def test_auth_service_uses_same_database_manager_as_context():
    context = build_app_context()

    assert context.auth_service.db is context.db
