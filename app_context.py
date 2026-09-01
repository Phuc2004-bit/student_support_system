from __future__ import annotations

from dataclasses import dataclass

from database.connection import DatabaseManager
from models.dto import UserSession
from services.auth_service import AuthService
from services.permission_service import PermissionService
from services.academic_service import AcademicService
from services.dashboard_contract import DashboardServiceContract


@dataclass
class AppContext:
    db: DatabaseManager
    auth_service: AuthService
    permission_service: PermissionService
    session: UserSession | None = None
    academic_service: AcademicService | None = None
    dashboard_service: DashboardServiceContract | None = None

    @property
    def is_authenticated(self) -> bool:
        return self.session is not None

    def set_session(
        self,
        session: UserSession,
    ) -> None:
        if session is None:
            raise ValueError(
                "UserSession không được để trống."
            )

        self.session = session

    def clear_session(self) -> None:
        self.session = None

    def can_manage_users(self) -> bool:
        return self._check_permission("can_manage_users")

    def can_manage_catalogs(self) -> bool:
        return self._check_permission("can_manage_catalogs")

    def can_manage_students(self) -> bool:
        return self._check_permission("can_manage_students")

    def can_manage_scores(self) -> bool:
        return self._check_permission("can_manage_scores")

    def can_manage_support(self) -> bool:
        return self._check_permission("can_manage_support")

    def can_view_reports(self) -> bool:
        return self._check_permission("can_view_reports")

    def require_admin(self) -> None:
        self._require_permission("require_admin")

    def require_manage_users(self) -> None:
        self._require_permission("require_manage_users")

    def require_manage_catalogs(self) -> None:
        self._require_permission("require_manage_catalogs")

    def require_manage_students(self) -> None:
        self._require_permission("require_manage_students")

    def require_manage_scores(self) -> None:
        self._require_permission("require_manage_scores")

    def require_manage_support(self) -> None:
        self._require_permission("require_manage_support")

    def require_view_reports(self) -> None:
        self._require_permission("require_view_reports")

    def _check_permission(
        self,
        method_name: str,
    ) -> bool:
        if self.session is None:
            return False

        method = getattr(
            self.permission_service,
            method_name,
        )

        return bool(method(self.session))

    def _require_permission(
        self,
        method_name: str,
    ) -> None:
        if self.session is None:
            raise PermissionError(
                "Người dùng chưa đăng nhập."
            )

        method = getattr(
            self.permission_service,
            method_name,
        )
        method(self.session)
