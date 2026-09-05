from contextlib import contextmanager
from datetime import datetime
import inspect

import pyodbc
import pytest

from exceptions import BusinessRuleError, DatabaseError, ValidationError
from models.dto import User, UserListItem, UserSession
from models.enums import UserRole
from repositories.user_repository import UserRepository
from services.user_service import UserService


NOW = datetime(2042, 2, 3, 4, 5, 6)


def make_user(user_id=1, role=UserRole.ADMIN, active=True):
    return User(
        user_id,
        "account_user",
        "OLD_HASH",
        "Account User",
        role,
        None,
        None,
        active,
        NOW,
        NOW,
    )


def make_session(user_id=1, role=UserRole.ADMIN, username="account_user"):
    return UserSession(user_id, username, "Account User", role)


class FakeDatabase:
    def __init__(self):
        self.connection = object()
        self.transactions = 0
        self.commits = 0
        self.rollbacks = 0

    @contextmanager
    def transaction(self):
        self.transactions += 1
        try:
            yield self.connection
        except Exception:
            self.rollbacks += 1
            raise
        else:
            self.commits += 1


class FakeRepository:
    def __init__(self, user=None):
        self.user = user or make_user()
        self.calls = []
        self.fail_on = None

    def get_profile_by_id(self, connection, user_id):
        if self.fail_on == "profile":
            raise pyodbc.Error("secret repository error")
        self.calls.append(("profile", user_id))
        if self.user is None or user_id != self.user.user_id:
            return None
        user = self.user
        return UserListItem(
            user.user_id,
            user.username,
            user.full_name,
            user.role,
            user.email,
            user.phone,
            user.is_active,
            user.created_at,
            user.updated_at,
        )

    def get_by_id(self, connection, user_id):
        self.calls.append(("get", user_id))
        return self.user if self.user and user_id == self.user.user_id else None

    def update_profile(self, connection, user_id, full_name, email, phone):
        if self.fail_on == "profile_update":
            raise pyodbc.Error("secret repository error")
        old = self.user
        self.user = User(
            old.user_id,
            old.username,
            old.password_hash,
            full_name,
            old.role,
            email,
            phone,
            old.is_active,
            old.created_at,
            NOW,
        )
        self.calls.append(("update_profile", user_id, full_name, email, phone))
        return self.user

    def update_password_hash(self, connection, user_id, password_hash):
        if self.fail_on == "password_update":
            raise pyodbc.Error("secret repository error")
        old = self.user
        self.user = User(
            old.user_id,
            old.username,
            password_hash,
            old.full_name,
            old.role,
            old.email,
            old.phone,
            old.is_active,
            old.created_at,
            NOW,
        )
        self.calls.append(("password", user_id, password_hash))
        return self.user


def build(user=None):
    db = FakeDatabase()
    repo = FakeRepository(user)
    return UserService(db, repo), db, repo


@pytest.mark.parametrize("role", [UserRole.ADMIN, UserRole.TEACHER])
def test_admin_and_teacher_load_only_their_safe_profile(role):
    user = make_user(role=role)
    service, db, repo = build(user)

    profile = service.get_own_profile(make_session(role=role))

    assert profile.user_id == user.user_id
    assert profile.role == role
    assert not hasattr(profile, "password_hash")
    assert repo.calls == [("profile", user.user_id)]
    assert db.commits == 1


@pytest.mark.parametrize(
    "actor,user",
    [
        (make_session(user_id=9), make_user()),
        (make_session(username="forged_user"), make_user()),
        (make_session(role=UserRole.TEACHER), make_user(role=UserRole.ADMIN)),
        (make_session(), make_user(active=False)),
    ],
)
def test_missing_forged_stale_or_inactive_session_is_blocked(actor, user):
    service, db, _ = build(user)

    with pytest.raises(ValidationError):
        service.get_own_profile(actor)

    assert db.rollbacks == 1


def test_update_own_profile_normalizes_safe_fields_and_preserves_identity():
    service, db, repo = build()

    updated = service.update_own_profile(
        make_session(),
        "  Updated Name  ",
        " updated@example.com ",
        " 0901234567 ",
    )

    assert updated.full_name == "Updated Name"
    assert updated.email == "updated@example.com"
    assert updated.phone == "0901234567"
    assert updated.username == "account_user"
    assert updated.role == UserRole.ADMIN
    assert updated.is_active is True
    assert not hasattr(updated, "password_hash")
    assert repo.user.password_hash == "OLD_HASH"
    assert db.commits == 1


@pytest.mark.parametrize(
    "full_name,email,phone",
    [
        ("", None, None),
        ("Name", "invalid-email", None),
        ("Name", None, "abc"),
    ],
)
def test_invalid_profile_data_is_blocked_before_transaction(full_name, email, phone):
    service, db, _ = build()

    with pytest.raises(ValidationError):
        service.update_own_profile(make_session(), full_name, email, phone)

    assert db.transactions == 0


def test_self_profile_api_has_no_target_role_or_active_parameters():
    signature = inspect.signature(UserService.update_own_profile)
    assert set(signature.parameters) == {
        "self",
        "actor",
        "full_name",
        "email",
        "phone",
    }


def test_change_password_verifies_current_hashes_new_and_returns_safe_dto(monkeypatch):
    service, db, repo = build()
    checks = []

    def verify(password, stored_hash):
        checks.append((password, stored_hash))
        return password == "Current@123"

    monkeypatch.setattr(UserService, "verify_password", staticmethod(verify))
    monkeypatch.setattr(
        UserService,
        "_hash_password",
        staticmethod(lambda password: "NEW_HASH"),
    )

    updated = service.change_own_password(
        make_session(), "Current@123", "Different@456"
    )

    assert checks == [
        ("Current@123", "OLD_HASH"),
        ("Different@456", "OLD_HASH"),
    ]
    assert repo.calls[-1] == ("password", 1, "NEW_HASH")
    assert repo.user.password_hash == "NEW_HASH"
    assert not hasattr(updated, "password_hash")
    assert "Current@123" not in repr(repo.calls)
    assert "Different@456" not in repr(repo.calls)
    assert db.commits == 1


def test_wrong_current_password_rolls_back_without_hash_or_update(monkeypatch):
    service, db, repo = build()
    hashes = []
    monkeypatch.setattr(UserService, "verify_password", staticmethod(lambda *_: False))
    monkeypatch.setattr(UserService, "_hash_password", staticmethod(hashes.append))

    with pytest.raises(ValidationError) as error:
        service.change_own_password(make_session(), "Wrong@123", "Different@456")

    assert str(error.value) == "Mật khẩu hiện tại không đúng."
    assert hashes == []
    assert not any(call[0] == "password" for call in repo.calls)
    assert db.rollbacks == 1


def test_same_password_is_blocked_after_current_password_verification(monkeypatch):
    service, db, repo = build()
    monkeypatch.setattr(UserService, "verify_password", staticmethod(lambda *_: True))

    with pytest.raises(BusinessRuleError):
        service.change_own_password(make_session(), "SamePass@123", "SamePass@123")

    assert not any(call[0] == "password" for call in repo.calls)
    assert db.rollbacks == 1


@pytest.mark.parametrize("new_password", ["short", "x" * 73, None])
def test_invalid_new_password_is_blocked_before_transaction(new_password):
    service, db, _ = build()

    with pytest.raises(ValidationError):
        service.change_own_password(make_session(), "Current@123", new_password)

    assert db.transactions == 0


@pytest.mark.parametrize("failure", ["profile", "profile_update", "password_update"])
def test_repository_failure_rolls_back_and_is_normalized(monkeypatch, failure):
    service, db, repo = build()
    repo.fail_on = failure
    monkeypatch.setattr(
        UserService,
        "verify_password",
        staticmethod(lambda password, _: password == "Current@123"),
    )
    monkeypatch.setattr(UserService, "_hash_password", staticmethod(lambda _: "HASH"))

    with pytest.raises(DatabaseError) as error:
        if failure == "profile":
            service.get_own_profile(make_session())
        elif failure == "profile_update":
            service.update_own_profile(make_session(), "Updated")
        else:
            service.change_own_password(
                make_session(), "Current@123", "Different@456"
            )

    assert "secret" not in str(error.value)
    assert db.rollbacks == 1


def test_repository_profile_query_is_parameterized_safe_and_never_commits():
    source = inspect.getsource(UserRepository)
    profile_source = inspect.getsource(UserRepository.get_profile_by_id)

    assert ".commit(" not in source
    assert "WHERE user_id = ?" in profile_source
    assert "password_hash" not in profile_source
