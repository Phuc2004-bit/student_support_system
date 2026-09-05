from contextlib import contextmanager
from dataclasses import fields
from datetime import datetime
import inspect

import pyodbc
import pytest

from exceptions import BusinessRuleError, DatabaseError, DuplicateError, ValidationError
from models.dto import User, UserListItem, UserSession
from models.enums import UserRole
from repositories.user_repository import UserRepository
from services.user_service import UserService


NOW = datetime(2042, 1, 2, 3, 4, 5)


def make_user(
    user_id=1,
    username="admin_one",
    role=UserRole.ADMIN,
    active=True,
    password_hash="$2b$12$stored",
):
    return User(
        user_id=user_id,
        username=username,
        password_hash=password_hash,
        full_name=f"User {user_id}",
        role=role,
        email=None,
        phone=None,
        is_active=active,
        created_at=NOW,
        updated_at=NOW,
    )


def admin_session(user_id=1):
    return UserSession(user_id, "admin_one", "Admin", UserRole.ADMIN)


def teacher_session():
    return UserSession(2, "teacher_one", "Teacher", UserRole.TEACHER)


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
    def __init__(self):
        self.users = {
            1: make_user(),
            2: make_user(2, "teacher_one", UserRole.TEACHER),
        }
        self.calls = []
        self.active_admins = 2
        self.fail = False

    def get_by_username(self, connection, username):
        return next((u for u in self.users.values() if u.username == username), None)

    def get_by_id(self, connection, user_id):
        return self.users.get(user_id)

    def list_for_management(self, connection, search=None):
        self.calls.append(("list", search))
        return [
            UserListItem(
                u.user_id,
                u.username,
                u.full_name,
                u.role,
                u.email,
                u.phone,
                u.is_active,
                u.created_at,
                u.updated_at,
            )
            for u in self.users.values()
            if search is None or search in u.username or search in u.full_name
        ]

    def create(
        self,
        connection,
        username,
        password_hash,
        full_name,
        role,
        email,
        phone,
        is_active,
    ):
        if self.fail:
            raise pyodbc.Error("repository failure")
        self.calls.append(("create", username, password_hash, role, is_active))
        user = User(
            3,
            username,
            password_hash,
            full_name,
            role,
            email,
            phone,
            is_active,
            NOW,
            NOW,
        )
        self.users[3] = user
        return user

    def update_management_details(
        self, connection, user_id, full_name, role, email, phone
    ):
        if self.fail:
            raise pyodbc.Error("repository failure")
        old = self.users.get(user_id)
        if old is None:
            return None
        updated = User(
            old.user_id,
            old.username,
            old.password_hash,
            full_name,
            role,
            email,
            phone,
            old.is_active,
            old.created_at,
            NOW,
        )
        self.users[user_id] = updated
        self.calls.append(("update", user_id, role))
        return updated

    def count_active_admins(self, connection):
        return self.active_admins

    def set_active(self, connection, user_id, is_active):
        if self.fail:
            raise pyodbc.Error("repository failure")
        old = self.users.get(user_id)
        if old is None:
            return None
        updated = User(
            old.user_id,
            old.username,
            old.password_hash,
            old.full_name,
            old.role,
            old.email,
            old.phone,
            is_active,
            old.created_at,
            NOW,
        )
        self.users[user_id] = updated
        self.calls.append(("active", user_id, is_active))
        return updated


def build():
    db = FakeDatabase()
    repo = FakeRepository()
    return UserService(db, repo), db, repo


def test_management_read_model_never_contains_password_hash():
    names = {field.name for field in fields(UserListItem)}
    assert "password_hash" not in names

    service, _, _ = build()
    result = service.admin_list_users(admin_session())
    assert result and not hasattr(result[0], "password_hash")


def test_admin_list_trims_search_and_service_owns_transaction():
    service, db, repo = build()

    service.admin_list_users(admin_session(), "  teacher  ")

    assert repo.calls == [("list", "teacher")]
    assert db.transactions == 1
    assert db.commits == 1


def test_teacher_cannot_use_any_management_api():
    service, db, _ = build()

    with pytest.raises(ValidationError):
        service.admin_list_users(teacher_session())
    with pytest.raises(ValidationError):
        service.admin_create_user(
            teacher_session(), "new_teacher", "Password@123", "New", UserRole.TEACHER
        )
    with pytest.raises(ValidationError):
        service.admin_update_user(
            teacher_session(), 2, "Teacher", UserRole.TEACHER
        )
    with pytest.raises(ValidationError):
        service.admin_set_user_active(teacher_session(), 2, False)

    assert db.transactions == 0


@pytest.mark.parametrize("role", [UserRole.ADMIN, UserRole.TEACHER])
def test_admin_create_uses_normalized_values_and_hash_only(monkeypatch, role):
    service, db, repo = build()
    monkeypatch.setattr(UserService, "_hash_password", staticmethod(lambda _: "HASHED"))

    created = service.admin_create_user(
        admin_session(),
        "  New_User  ",
        "Password@123",
        "  New User  ",
        role,
        "  new@example.com  ",
        "  0901234567  ",
        True,
    )

    assert created.username == "new_user"
    assert created.password_hash == "HASHED"
    assert repo.calls[-1] == ("create", "new_user", "HASHED", role, True)
    assert "Password@123" not in repr(repo.calls)
    assert db.commits == 1


@pytest.mark.parametrize(
    "username,password,role,is_active",
    [
        ("", "Password@123", UserRole.TEACHER, True),
        ("new_user", "short", UserRole.TEACHER, True),
        ("new_user", "Password@123", "TEACHER", True),
        ("new_user", "Password@123", UserRole.TEACHER, "yes"),
    ],
)
def test_invalid_create_is_blocked_before_transaction(
    username, password, role, is_active
):
    service, db, _ = build()

    with pytest.raises(ValidationError):
        service.admin_create_user(
            admin_session(), username, password, "User", role, is_active=is_active
        )

    assert db.transactions == 0


def test_duplicate_username_rolls_back_without_hashing(monkeypatch):
    service, db, _ = build()
    hashed = []
    monkeypatch.setattr(UserService, "_hash_password", staticmethod(hashed.append))

    with pytest.raises(DuplicateError):
        service.admin_create_user(
            admin_session(), "ADMIN_ONE", "Password@123", "Duplicate", UserRole.ADMIN
        )

    assert hashed == []
    assert db.rollbacks == 1


def test_update_changes_safe_fields_but_preserves_username_hash_and_active():
    service, db, repo = build()
    before = repo.users[2]

    updated = service.admin_update_user(
        admin_session(),
        2,
        "  Updated Teacher  ",
        UserRole.ADMIN,
        " updated@example.com ",
        " 0901234567 ",
    )

    assert updated.full_name == "Updated Teacher"
    assert updated.role == UserRole.ADMIN
    assert updated.username == before.username
    assert updated.password_hash == before.password_hash
    assert updated.is_active == before.is_active
    assert db.commits == 1


def test_current_admin_cannot_demote_or_deactivate_self():
    service, db, repo = build()

    with pytest.raises(BusinessRuleError):
        service.admin_update_user(admin_session(), 1, "Admin", UserRole.TEACHER)
    with pytest.raises(BusinessRuleError):
        service.admin_set_user_active(admin_session(), 1, False)

    assert not any(call[0] in {"update", "active"} for call in repo.calls)
    assert db.rollbacks == 2


@pytest.mark.parametrize("operation", ["demote", "deactivate"])
def test_last_active_admin_is_protected(operation):
    service, db, repo = build()
    repo.users[9] = make_user(9, "last_admin")
    repo.active_admins = 1

    with pytest.raises(BusinessRuleError):
        if operation == "demote":
            service.admin_update_user(admin_session(), 9, "Last", UserRole.TEACHER)
        else:
            service.admin_set_user_active(admin_session(), 9, False)

    assert db.rollbacks == 1


def test_deactivate_and_reactivate_use_service_transaction():
    service, db, repo = build()

    assert service.admin_set_user_active(admin_session(), 2, False).is_active is False
    assert service.admin_set_user_active(admin_session(), 2, True).is_active is True
    assert repo.calls[-2:] == [("active", 2, False), ("active", 2, True)]
    assert db.commits == 2


def test_invalid_update_rolls_back_and_repository_error_is_normalized():
    service, db, repo = build()
    with pytest.raises(ValidationError):
        service.admin_update_user(admin_session(), 999, "Missing", UserRole.TEACHER)
    repo.fail = True
    with pytest.raises(DatabaseError) as error:
        service.admin_set_user_active(admin_session(), 2, False)

    assert "repository failure" not in str(error.value)
    assert db.rollbacks == 2


def test_repository_management_methods_are_parameterized_and_never_commit():
    source = inspect.getsource(UserRepository)
    list_source = inspect.getsource(UserRepository.list_for_management)

    assert ".commit(" not in source
    assert "SELECT *" not in source.upper()
    assert "password_hash" not in list_source
    assert "LIKE ?" in list_source
    assert "WHERE user_id = ?" in inspect.getsource(
        UserRepository.update_management_details
    )
    assert not hasattr(UserRepository, "delete")
