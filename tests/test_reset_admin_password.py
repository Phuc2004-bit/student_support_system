from __future__ import annotations

from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime
import inspect

import pytest

from exceptions import BusinessRuleError, ValidationError
from models.dto import User
from models.enums import UserRole
from scripts import reset_admin_password
from services.auth_service import AuthService
from services.user_service import UserService


NOW = datetime(2042, 1, 2, 3, 4, 5)
OLD_PASSWORD = "OldPassword@123"
NEW_PASSWORD = "NewPassword@456"


def make_user(
    username: str = "admin",
    role: UserRole = UserRole.ADMIN,
    active: bool = True,
) -> User:
    return User(
        user_id=7,
        username=username,
        password_hash=UserService._hash_password(OLD_PASSWORD),
        full_name="Existing Admin",
        role=role,
        email="admin@example.com",
        phone="0900000000",
        is_active=active,
        created_at=NOW,
        updated_at=NOW,
    )


class FakeDatabase:
    def __init__(self):
        self.connection = object()
        self.transactions = 0
        self.commits = 0
        self.rollbacks = 0
        self.connection_closed = False

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

    def get_connection(self):
        database = self

        class Connection:
            def close(self):
                database.connection_closed = True

        return Connection()


class PersistingRepository:
    def __init__(self, user: User | None):
        self.user = user
        self.updated_ids: list[int] = []

    def get_by_username(self, connection, username):
        if self.user is None or self.user.username != username:
            return None
        return self.user

    def update_password_hash(self, connection, user_id, password_hash):
        if self.user is None or self.user.user_id != user_id:
            return None
        self.updated_ids.append(user_id)
        self.user = replace(self.user, password_hash=password_hash)
        return self.user


def services(user: User | None):
    db = FakeDatabase()
    repository = PersistingRepository(user)
    return db, repository, UserService(db, repository), AuthService(db, repository)


def run_script(user, inputs, passwords):
    db, repository, user_service, auth_service = services(user)
    outputs: list[str] = []
    input_values = iter(inputs)
    password_values = iter(passwords)
    result = reset_admin_password.run(
        input_fn=lambda _prompt: next(input_values),
        password_fn=lambda _prompt: next(password_values),
        output_fn=outputs.append,
        services_factory=lambda: (db, user_service, auth_service),
    )
    return result, outputs, db, repository


def test_service_resets_admin_in_one_transaction_and_new_password_authenticates():
    original = make_user()
    db, repository, service, auth_service = services(original)

    updated = service.reset_admin_password(" ADMIN ", NEW_PASSWORD)
    session = auth_service.login("admin", NEW_PASSWORD)

    assert session.user_id == original.user_id
    assert session.role is UserRole.ADMIN
    assert updated.username == original.username
    assert updated.role is original.role
    assert updated.is_active == original.is_active
    assert updated.full_name == original.full_name
    assert updated.email == original.email
    assert updated.phone == original.phone
    assert repository.updated_ids == [original.user_id]
    assert int(updated.password_hash.split("$")[2]) == 12
    assert service.verify_password(NEW_PASSWORD, updated.password_hash)
    assert not service.verify_password(OLD_PASSWORD, updated.password_hash)
    assert db.transactions == db.commits == 2  # reset, then AuthService login


def test_service_unknown_user_fails_without_hash_update():
    db, repository, service, _auth = services(None)

    with pytest.raises(ValidationError, match="người dùng"):
        service.reset_admin_password("missing", NEW_PASSWORD)

    assert repository.updated_ids == []
    assert db.rollbacks == 1


def test_service_non_admin_fails_without_hash_update():
    db, repository, service, _auth = services(make_user(role=UserRole.TEACHER))

    with pytest.raises(BusinessRuleError, match="ADMIN"):
        service.reset_admin_password("admin", NEW_PASSWORD)

    assert repository.updated_ids == []
    assert db.rollbacks == 1


def test_script_success_uses_default_admin_and_verifies_login():
    result, outputs, db, repository = run_script(
        make_user(), [""], [NEW_PASSWORD, NEW_PASSWORD]
    )

    assert result == 0
    assert repository.updated_ids == [7]
    assert db.connection_closed is True
    assert any("admin" in line and "thành công" in line for line in outputs)
    assert all(NEW_PASSWORD not in line and OLD_PASSWORD not in line for line in outputs)


def test_script_unknown_user_stops_before_password_prompt():
    result, outputs, _db, repository = run_script(None, ["missing"], [])

    assert result == 3
    assert repository.updated_ids == []
    assert any("Không tìm thấy" in line for line in outputs)


def test_script_non_admin_stops_before_password_prompt():
    result, outputs, _db, repository = run_script(
        make_user(role=UserRole.TEACHER), ["admin"], []
    )

    assert result == 4
    assert repository.updated_ids == []
    assert any("không có role ADMIN" in line for line in outputs)


def test_script_password_mismatch_does_not_update():
    result, outputs, _db, repository = run_script(
        make_user(), ["admin"], [NEW_PASSWORD, "Different@789"]
    )

    assert result == 6
    assert repository.updated_ids == []
    assert any("không khớp" in line for line in outputs)


def test_script_password_policy_failure_does_not_update_or_expose_value():
    rejected = "short"
    result, outputs, _db, repository = run_script(
        make_user(), ["admin"], [rejected, rejected]
    )

    assert result == 7
    assert repository.updated_ids == []
    assert all(rejected not in line for line in outputs)


def test_script_refuses_inactive_admin_to_keep_auth_verification_possible():
    result, outputs, _db, repository = run_script(
        make_user(active=False), ["admin"], []
    )

    assert result == 5
    assert repository.updated_ids == []
    assert any("vô hiệu hóa" in line for line in outputs)


def test_script_uses_getpass_and_never_exposes_hash_or_direct_sql():
    source = inspect.getsource(reset_admin_password)

    assert "getpass.getpass" in source
    assert "reset_admin_password(username, new_password)" in source
    assert "password_hash" not in source
    assert "UPDATE " not in source.upper()
    assert "commit(" not in source
