import pytest

from exceptions import ValidationError
from models.dto import UserSession
from models.enums import UserRole
from services import PermissionService


def make_admin_session() -> UserSession:
    return UserSession(
        user_id=1,
        username="admin_test",
        full_name="Quản Trị Test",
        role=UserRole.ADMIN,
    )


def make_teacher_session() -> UserSession:
    return UserSession(
        user_id=2,
        username="teacher_test",
        full_name="Giáo Viên Test",
        role=UserRole.TEACHER,
    )


def test_permission_service_admin_and_teacher():
    admin = make_admin_session()
    teacher = make_teacher_session()

    assert PermissionService.is_admin(admin) is True
    assert PermissionService.is_teacher(admin) is False

    assert PermissionService.can_manage_users(admin) is True
    assert PermissionService.can_access_system(admin) is True
    assert PermissionService.can_manage_catalogs(admin) is True
    assert PermissionService.can_manage_students(admin) is True
    assert PermissionService.can_manage_scores(admin) is True
    assert PermissionService.can_manage_support(admin) is True
    assert PermissionService.can_view_reports(admin) is True

    PermissionService.require_admin(admin)
    PermissionService.require_teacher_or_admin(admin)
    PermissionService.require_manage_users(admin)
    PermissionService.require_access_system(admin)
    PermissionService.require_manage_catalogs(admin)
    PermissionService.require_manage_students(admin)
    PermissionService.require_manage_scores(admin)
    PermissionService.require_manage_support(admin)
    PermissionService.require_view_reports(admin)

    assert PermissionService.is_admin(teacher) is False
    assert PermissionService.is_teacher(teacher) is True

    assert PermissionService.can_manage_users(teacher) is False
    assert PermissionService.can_access_system(teacher) is True
    assert PermissionService.can_manage_catalogs(teacher) is False

    assert PermissionService.can_manage_students(teacher) is True
    assert PermissionService.can_manage_scores(teacher) is True
    assert PermissionService.can_manage_support(teacher) is True
    assert PermissionService.can_view_reports(teacher) is True

    with pytest.raises(ValidationError):
        PermissionService.require_admin(teacher)

    with pytest.raises(ValidationError):
        PermissionService.require_manage_users(teacher)

    PermissionService.require_access_system(teacher)

    with pytest.raises(ValidationError):
        PermissionService.require_manage_catalogs(teacher)

    PermissionService.require_teacher_or_admin(teacher)
    PermissionService.require_manage_students(teacher)
    PermissionService.require_manage_scores(teacher)
    PermissionService.require_manage_support(teacher)
    PermissionService.require_view_reports(teacher)


def test_permission_service_invalid_session():
    with pytest.raises(ValidationError):
        PermissionService.is_admin(None)

    invalid_user_id = UserSession(
        user_id=0,
        username="invalid",
        full_name="Invalid User",
        role=UserRole.TEACHER,
    )

    with pytest.raises(ValidationError):
        PermissionService.can_manage_scores(invalid_user_id)

    invalid_username = UserSession(
        user_id=3,
        username="",
        full_name="Invalid User",
        role=UserRole.TEACHER,
    )

    with pytest.raises(ValidationError):
        PermissionService.can_manage_support(invalid_username)
