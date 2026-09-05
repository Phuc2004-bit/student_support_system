import pytest

from app_context import AppContext
from exceptions import ValidationError
from models.dto import UserSession
from models.enums import UserRole
from services.permission_service import PermissionService


class FakeDatabase:
    pass


class FakeAuthService:
    pass


def make_context(
    session: UserSession | None = None,
) -> AppContext:
    return AppContext(
        db=FakeDatabase(),
        auth_service=FakeAuthService(),
        permission_service=PermissionService(),
        session=session,
    )


def make_admin_session() -> UserSession:
    return UserSession(
        user_id=1,
        username="admin",
        full_name="Quản trị viên",
        role=UserRole.ADMIN,
    )


def make_teacher_session() -> UserSession:
    return UserSession(
        user_id=2,
        username="teacher",
        full_name="Giáo viên",
        role=UserRole.TEACHER,
    )


def test_unauthenticated_context_denies_all_can_checks():
    context = make_context()

    assert context.is_authenticated is False
    assert context.can_manage_users() is False
    assert context.can_access_system() is False
    assert context.can_manage_catalogs() is False
    assert context.can_manage_students() is False
    assert context.can_manage_scores() is False
    assert context.can_manage_support() is False
    assert context.can_view_reports() is False


def test_admin_context_has_all_v1_permissions():
    context = make_context(
        make_admin_session()
    )

    assert context.can_manage_users() is True
    assert context.can_access_system() is True
    assert context.can_manage_catalogs() is True
    assert context.can_manage_students() is True
    assert context.can_manage_scores() is True
    assert context.can_manage_support() is True
    assert context.can_view_reports() is True

    context.require_admin()
    context.require_manage_users()
    context.require_access_system()
    context.require_manage_catalogs()
    context.require_manage_students()
    context.require_manage_scores()
    context.require_manage_support()
    context.require_view_reports()


def test_teacher_context_matches_permission_matrix():
    context = make_context(
        make_teacher_session()
    )

    assert context.can_manage_users() is False
    assert context.can_access_system() is True
    assert context.can_manage_catalogs() is False

    assert context.can_manage_students() is True
    assert context.can_manage_scores() is True
    assert context.can_manage_support() is True
    assert context.can_view_reports() is True

    with pytest.raises(ValidationError):
        context.require_admin()

    with pytest.raises(ValidationError):
        context.require_manage_users()

    context.require_access_system()

    with pytest.raises(ValidationError):
        context.require_manage_catalogs()

    context.require_manage_students()
    context.require_manage_scores()
    context.require_manage_support()
    context.require_view_reports()


def test_clear_session_immediately_removes_permissions():
    context = make_context(
        make_admin_session()
    )

    assert context.can_manage_users() is True

    context.clear_session()

    assert context.is_authenticated is False
    assert context.can_manage_users() is False
    assert context.can_access_system() is False
    assert context.can_manage_students() is False

    with pytest.raises(PermissionError):
        context.require_manage_users()
