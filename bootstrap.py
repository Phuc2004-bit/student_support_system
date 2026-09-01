from __future__ import annotations

from config.database import db_settings
from database.connection import DatabaseManager
from services.auth_service import AuthService
from services.academic_service import AcademicService
from services.dashboard_service import DashboardService
from services.permission_service import PermissionService
from app_context import AppContext


def build_app_context() -> AppContext:
    """
    Composition root của ứng dụng.

    Đây là nơi duy nhất chịu trách nhiệm khởi tạo các dependency cấp cao
    cần cho quá trình đăng nhập/khởi động ứng dụng.
    """
    db = DatabaseManager(
        db_settings.connection_string()
    )

    auth_service = AuthService(db=db)
    permission_service = PermissionService()
    academic_service = AcademicService(db=db)
    dashboard_service = DashboardService(db=db)

    return AppContext(
        db=db,
        auth_service=auth_service,
        permission_service=permission_service,
        academic_service=academic_service,
        dashboard_service=dashboard_service,
    )
