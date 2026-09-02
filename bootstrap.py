from __future__ import annotations

from config.database import db_settings
from database.connection import DatabaseManager
from services.auth_service import AuthService
from services.academic_service import AcademicService
from services.dashboard_service import DashboardService
from services.permission_service import PermissionService
from services.enrollment_service import EnrollmentService
from services.student_list_service import StudentListService
from services.student_profile_service import StudentProfileService
from services.student_service import StudentService
from services.score_service import ScoreService
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
    student_list_service = StudentListService(db=db)
    student_service = StudentService(db=db)
    enrollment_service = EnrollmentService(db=db)
    student_profile_service = StudentProfileService(db=db)
    score_service = ScoreService(db=db)

    return AppContext(
        db=db,
        auth_service=auth_service,
        permission_service=permission_service,
        academic_service=academic_service,
        dashboard_service=dashboard_service,
        student_list_service=student_list_service,
        student_service=student_service,
        enrollment_service=enrollment_service,
        student_profile_service=student_profile_service,
        score_service=score_service,
    )
