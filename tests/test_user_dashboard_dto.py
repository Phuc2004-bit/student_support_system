from datetime import datetime

from models.dto import (
    DashboardSummary,
    User,
    UserSession,
)
from models.enums import UserRole


def test_create_user():
    now = datetime.now()

    user = User(
        user_id=1,
        username="admin",
        password_hash="$2b$...",
        full_name="Quản trị viên",
        role=UserRole.ADMIN,
        email=None,
        phone=None,
        is_active=True,
        created_at=now,
        updated_at=now,
    )

    assert user.username == "admin"
    assert user.role == UserRole.ADMIN
    assert user.is_active is True


def test_user_session_does_not_require_password_hash():
    session = UserSession(
        user_id=1,
        username="admin",
        full_name="Quản trị viên",
        role=UserRole.ADMIN,
    )

    assert session.user_id == 1
    assert session.role == UserRole.ADMIN
    assert not hasattr(session, "password_hash")


def test_dashboard_summary():
    summary = DashboardSummary(
        total_students=1000,
        need_support=120,
        in_progress=80,
        waiting_review=20,
        completed=50,
        continue_count=10,
    )

    assert summary.total_students == 1000
    assert summary.need_support == 120
    assert summary.completed == 50