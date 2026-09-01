from app_context import AppContext
from bootstrap import build_app_context
from database.connection import DatabaseManager
from services.auth_service import AuthService
from services.permission_service import PermissionService
from services.enrollment_service import EnrollmentService
from services.student_list_service import StudentListService
from services.student_profile_service import StudentProfileService
from services.student_service import StudentService


def test_build_app_context_creates_core_dependencies():
    context = build_app_context()

    assert isinstance(context, AppContext)
    assert isinstance(context.db, DatabaseManager)
    assert isinstance(context.auth_service, AuthService)
    assert isinstance(
        context.permission_service,
        PermissionService,
    )
    assert isinstance(context.student_list_service, StudentListService)
    assert isinstance(context.student_service, StudentService)
    assert isinstance(context.enrollment_service, EnrollmentService)
    assert isinstance(
        context.student_profile_service,
        StudentProfileService,
    )


def test_auth_service_uses_same_database_manager_as_context():
    context = build_app_context()

    assert context.auth_service.db is context.db
