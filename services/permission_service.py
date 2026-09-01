from exceptions import ValidationError
from models.dto import UserSession
from models.enums import UserRole


class PermissionService:
    """
    Xử lý phân quyền nghiệp vụ của hệ thống.

    Nguyên tắc:
    - ADMIN: có toàn bộ quyền quản trị.
    - TEACHER: có quyền nghiệp vụ học sinh, điểm và bổ trợ.
    - Logic phân quyền nằm ở Service, không rải rác trong UI.
    """

    # =====================================================
    # BASIC CHECKS
    # =====================================================

    @staticmethod
    def is_admin(
        session: UserSession,
    ) -> bool:
        PermissionService._validate_session(session)

        return session.role == UserRole.ADMIN

    @staticmethod
    def is_teacher(
        session: UserSession,
    ) -> bool:
        PermissionService._validate_session(session)

        return session.role == UserRole.TEACHER

    # =====================================================
    # USER MANAGEMENT
    # =====================================================

    @staticmethod
    def can_manage_users(
        session: UserSession,
    ) -> bool:
        """
        Chỉ ADMIN được quản lý tài khoản.
        """
        PermissionService._validate_session(session)

        return session.role == UserRole.ADMIN

    @staticmethod
    def require_manage_users(
        session: UserSession,
    ) -> None:
        if not PermissionService.can_manage_users(session):
            raise ValidationError(
                "Bạn không có quyền quản lý tài khoản."
            )

    # =====================================================
    # CATALOG MANAGEMENT
    # =====================================================

    @staticmethod
    def can_manage_catalogs(
        session: UserSession,
    ) -> bool:
        """
        Danh mục nền:
        - năm học
        - khối
        - lớp
        - môn học
        - quy tắc bổ trợ

        V1.0: chỉ ADMIN được thay đổi.
        """
        PermissionService._validate_session(session)

        return session.role == UserRole.ADMIN

    @staticmethod
    def require_manage_catalogs(
        session: UserSession,
    ) -> None:
        if not PermissionService.can_manage_catalogs(session):
            raise ValidationError(
                "Bạn không có quyền quản lý danh mục."
            )

    # =====================================================
    # STUDENT MANAGEMENT
    # =====================================================

    @staticmethod
    def can_manage_students(
        session: UserSession,
    ) -> bool:
        """
        ADMIN và TEACHER đều có thể thực hiện
        nghiệp vụ học sinh trong V1.0.
        """
        PermissionService._validate_session(session)

        return session.role in {
            UserRole.ADMIN,
            UserRole.TEACHER,
        }

    @staticmethod
    def require_manage_students(
        session: UserSession,
    ) -> None:
        if not PermissionService.can_manage_students(session):
            raise ValidationError(
                "Bạn không có quyền quản lý học sinh."
            )

    # =====================================================
    # SCORE MANAGEMENT
    # =====================================================

    @staticmethod
    def can_manage_scores(
        session: UserSession,
    ) -> bool:
        """
        ADMIN và TEACHER được nhập/cập nhật điểm
        theo phạm vi nghiệp vụ của V1.0.
        """
        PermissionService._validate_session(session)

        return session.role in {
            UserRole.ADMIN,
            UserRole.TEACHER,
        }

    @staticmethod
    def require_manage_scores(
        session: UserSession,
    ) -> None:
        if not PermissionService.can_manage_scores(session):
            raise ValidationError(
                "Bạn không có quyền quản lý điểm."
            )

    # =====================================================
    # SUPPORT MANAGEMENT
    # =====================================================

    @staticmethod
    def can_manage_support(
        session: UserSession,
    ) -> bool:
        """
        ADMIN và TEACHER được thực hiện workflow bổ trợ.
        """
        PermissionService._validate_session(session)

        return session.role in {
            UserRole.ADMIN,
            UserRole.TEACHER,
        }

    @staticmethod
    def require_manage_support(
        session: UserSession,
    ) -> None:
        if not PermissionService.can_manage_support(session):
            raise ValidationError(
                "Bạn không có quyền thực hiện "
                "nghiệp vụ bổ trợ."
            )

    # =====================================================
    # REPORTS
    # =====================================================

    @staticmethod
    def can_view_reports(
        session: UserSession,
    ) -> bool:
        """
        ADMIN và TEACHER đều được xem báo cáo.
        """
        PermissionService._validate_session(session)

        return session.role in {
            UserRole.ADMIN,
            UserRole.TEACHER,
        }

    @staticmethod
    def require_view_reports(
        session: UserSession,
    ) -> None:
        if not PermissionService.can_view_reports(session):
            raise ValidationError(
                "Bạn không có quyền xem báo cáo."
            )

    # =====================================================
    # GENERIC ROLE REQUIREMENTS
    # =====================================================

    @staticmethod
    def require_admin(
        session: UserSession,
    ) -> None:
        PermissionService._validate_session(session)

        if session.role != UserRole.ADMIN:
            raise ValidationError(
                "Chức năng này chỉ dành cho ADMIN."
            )

    @staticmethod
    def require_teacher_or_admin(
        session: UserSession,
    ) -> None:
        PermissionService._validate_session(session)

        if session.role not in {
            UserRole.ADMIN,
            UserRole.TEACHER,
        }:
            raise ValidationError(
                "Bạn không có quyền thực hiện "
                "chức năng này."
            )

    # =====================================================
    # VALIDATION
    # =====================================================

    @staticmethod
    def _validate_session(
        session: UserSession,
    ) -> None:
        if session is None:
            raise ValidationError(
                "Phiên đăng nhập không hợp lệ."
            )

        if session.user_id <= 0:
            raise ValidationError(
                "Phiên đăng nhập không hợp lệ."
            )

        if not session.username:
            raise ValidationError(
                "Phiên đăng nhập không hợp lệ."
            )

        if not isinstance(session.role, UserRole):
            raise ValidationError(
                "Vai trò người dùng không hợp lệ."
            )