from contextlib import contextmanager
from datetime import datetime
from threading import Event, Lock, Thread

import bcrypt
import pyodbc
import pytest

from config.database import db_settings
from database.connection import DatabaseManager
from exceptions import BusinessRuleError, DatabaseError, DuplicateError
from models.dto import User, UserSession
from models.enums import UserRole
from repositories.user_repository import UserRepository
from scripts.create_initial_admin import run
from services.auth_service import AuthService
from services.user_service import UserService


NOW = datetime(2042, 1, 2, 3, 4, 5)


def make_user(username="first_admin", role=UserRole.ADMIN, active=True):
    return User(
        user_id=1,
        username=username,
        password_hash="$2b$12$not-printed",
        full_name="First Admin",
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


class FakeRepository:
    def __init__(self, *, existing=None, active_admins=0, lock_result=0):
        self.existing = existing
        self.active_admins = active_admins
        self.lock_result = lock_result
        self.created = []
        self.bootstrap_lock_results = []

    def acquire_initial_admin_bootstrap_lock(self, connection):
        self.bootstrap_lock_results.append(connection)
        return self.lock_result

    def get_by_username(self, connection, username):
        return self.existing

    def count_active_admins(self, connection):
        return self.active_admins

    def create(self, connection, **values):
        self.created.append(values)
        return make_user(values["username"], values["role"], values["is_active"])


def test_service_creates_only_first_active_admin_in_its_transaction(monkeypatch):
    db = FakeDatabase()
    repository = FakeRepository()
    service = UserService(db, repository)
    monkeypatch.setattr(service, "_hash_password", lambda password: "bcrypt-hash")

    created = service.create_initial_admin(
        " First_Admin ",
        "Password@123",
        " First Admin ",
        "admin@example.com",
        "0900000000",
    )

    assert created.username == "first_admin"
    assert created.role is UserRole.ADMIN
    assert created.is_active is True
    assert repository.created[0]["password_hash"] == "bcrypt-hash"
    assert repository.created[0]["role"] is UserRole.ADMIN
    assert repository.created[0]["is_active"] is True
    assert repository.bootstrap_lock_results == [db.connection]
    assert db.transactions == db.commits == 1
    assert db.rollbacks == 0


def test_service_refuses_when_an_active_admin_exists():
    db = FakeDatabase()
    repository = FakeRepository(active_admins=1)
    service = UserService(db, repository)

    with pytest.raises(BusinessRuleError, match="ADMIN"):
        service.create_initial_admin("new_admin", "Password@123", "New Admin")

    assert repository.created == []
    assert db.rollbacks == 1


def test_service_never_overwrites_an_existing_username():
    db = FakeDatabase()
    repository = FakeRepository(existing=make_user())
    service = UserService(db, repository)

    with pytest.raises(DuplicateError):
        service.create_initial_admin("first_admin", "Password@123", "First Admin")

    assert repository.created == []
    assert db.rollbacks == 1


def test_service_rolls_back_when_create_fails():
    class FailingRepository(FakeRepository):
        def create(self, connection, **values):
            raise pyodbc.Error("simulated write failure")

    db = FakeDatabase()
    repository = FailingRepository()
    service = UserService(db, repository)

    with pytest.raises(DatabaseError, match="Không thể tạo ADMIN"):
        service.create_initial_admin(
            "first_admin",
            "Password@123",
            "First Admin",
        )

    assert db.commits == 0
    assert db.rollbacks == 1


def test_lock_failure_is_normalized_without_exposing_sql_server_details():
    db = FakeDatabase()
    repository = FakeRepository(lock_result=-1)
    service = UserService(db, repository)

    with pytest.raises(DatabaseError) as caught:
        service.create_initial_admin(
            "first_admin",
            "Password@123",
            "First Admin",
        )

    assert "khóa thao tác" in str(caught.value)
    assert "sp_getapplock" not in str(caught.value)
    assert repository.created == []
    assert db.rollbacks == 1


def test_repository_application_lock_is_parameterized_and_never_commits():
    class Cursor:
        def __init__(self):
            self.call = None

        def execute(self, statement, *params):
            self.call = (statement, params)
            return self

        def fetchone(self):
            return (0,)

    class Connection:
        def __init__(self):
            self.cursor_instance = Cursor()
            self.commit_calls = 0

        def cursor(self):
            return self.cursor_instance

        def commit(self):
            self.commit_calls += 1

    connection = Connection()
    repository = UserRepository()

    result = repository.acquire_initial_admin_bootstrap_lock(connection)

    statement, params = connection.cursor_instance.call
    assert result == 0
    assert "SP_GETAPPLOCK" in statement.upper()
    assert "LOCKOWNER = 'TRANSACTION'" in statement.upper().replace("@", "")
    assert params == (
        repository.INITIAL_ADMIN_BOOTSTRAP_LOCK_RESOURCE,
        15_000,
    )
    assert connection.commit_calls == 0


def test_initial_admin_password_keeps_bcrypt_rounds_12():
    password_hash = UserService._hash_password("Password@123")

    assert password_hash.startswith("$2")
    assert int(password_hash.split("$")[2]) == 12
    assert bcrypt.checkpw(
        b"Password@123",
        password_hash.encode("utf-8"),
    )


def test_normal_user_creation_can_still_create_another_admin(monkeypatch):
    db = FakeDatabase()
    repository = FakeRepository(active_admins=1)
    service = UserService(db, repository)
    monkeypatch.setattr(service, "_hash_password", lambda password: "bcrypt-hash")

    created = service.create_user(
        "second_admin",
        "Password@123",
        "Second Admin",
        UserRole.ADMIN,
    )

    assert created.role is UserRole.ADMIN
    assert repository.bootstrap_lock_results == []
    assert repository.created[0]["username"] == "second_admin"


def test_initial_admin_can_log_in_through_real_auth_service():
    class PersistingRepository(FakeRepository):
        def get_by_username(self, connection, username):
            return self.existing

        def create(self, connection, **values):
            self.existing = User(
                user_id=1,
                username=values["username"],
                password_hash=values["password_hash"],
                full_name=values["full_name"],
                role=values["role"],
                email=values["email"],
                phone=values["phone"],
                is_active=values["is_active"],
                created_at=NOW,
                updated_at=NOW,
            )
            return self.existing

    db = FakeDatabase()
    repository = PersistingRepository()
    user_service = UserService(db, repository)
    auth_service = AuthService(db, repository)

    created = user_service.create_initial_admin(
        "first_admin",
        "Password@123",
        "First Admin",
    )
    session = auth_service.login(created.username, "Password@123")

    assert session.user_id == created.user_id
    assert session.role is UserRole.ADMIN
    assert created.is_active is True


def _test_database_manager() -> DatabaseManager:
    connection_string = db_settings.connection_string().replace(
        "DATABASE=student_support_db;",
        "DATABASE=student_support_db_test;",
    )
    normalized = connection_string.upper().replace(" ", "")
    if "DATABASE=STUDENT_SUPPORT_DB_TEST;" not in normalized:
        raise RuntimeError("Concurrency test requires student_support_db_test.")
    return DatabaseManager(connection_string)


def test_two_real_database_transactions_bootstrap_only_one_initial_admin():
    db = _test_database_manager()
    with db.transaction() as connection:
        actual_database = connection.cursor().execute(
            "SELECT DB_NAME()"
        ).fetchone()[0]
    assert actual_database == "student_support_db_test"

    class ConcurrentRepository:
        def __init__(self):
            self._lock_repository = UserRepository()
            self._state_lock = Lock()
            self._users = {}
            self._lock_attempts = 0
            self._count_calls = 0
            self.connection_ids = []
            self.first_inside = Event()
            self.release_first = Event()
            self.second_attempting = Event()
            self.second_entered = Event()

        def acquire_initial_admin_bootstrap_lock(self, connection):
            with self._state_lock:
                self._lock_attempts += 1
                attempt = self._lock_attempts
                self.connection_ids.append(id(connection))
            if attempt == 2:
                self.second_attempting.set()
            result = self._lock_repository.acquire_initial_admin_bootstrap_lock(
                connection
            )
            if attempt == 2:
                self.second_entered.set()
            return result

        def get_by_username(self, connection, username):
            with self._state_lock:
                return self._users.get(username)

        def count_active_admins(self, connection):
            with self._state_lock:
                self._count_calls += 1
                count_call = self._count_calls
            if count_call == 1:
                self.first_inside.set()
                if not self.release_first.wait(timeout=10):
                    raise AssertionError("First bootstrap was not released.")
            with self._state_lock:
                return sum(
                    user.role is UserRole.ADMIN and user.is_active
                    for user in self._users.values()
                )

        def create(self, connection, **values):
            with self._state_lock:
                created = User(
                    user_id=len(self._users) + 1,
                    username=values["username"],
                    password_hash=values["password_hash"],
                    full_name=values["full_name"],
                    role=values["role"],
                    email=values["email"],
                    phone=values["phone"],
                    is_active=values["is_active"],
                    created_at=NOW,
                    updated_at=NOW,
                )
                self._users[created.username] = created
                return created

    repository = ConcurrentRepository()
    services = (UserService(db, repository), UserService(db, repository))
    outcomes = []
    outcome_lock = Lock()

    def bootstrap(service, username):
        try:
            result = service.create_initial_admin(
                username,
                "Password@123",
                f"Admin {username[-1]}",
            )
        except Exception as exc:  # Captured for assertions in the main thread.
            result = exc
        with outcome_lock:
            outcomes.append(result)

    first = Thread(target=bootstrap, args=(services[0], "race_admin_1"))
    second = Thread(target=bootstrap, args=(services[1], "race_admin_2"))
    first.start()
    assert repository.first_inside.wait(timeout=10)
    second.start()
    assert repository.second_attempting.wait(timeout=10)
    assert not repository.second_entered.wait(timeout=0.25)
    repository.release_first.set()
    first.join(timeout=20)
    second.join(timeout=20)

    assert not first.is_alive()
    assert not second.is_alive()
    assert len(set(repository.connection_ids)) == 2
    assert len([item for item in outcomes if isinstance(item, User)]) == 1
    losers = [item for item in outcomes if isinstance(item, BusinessRuleError)]
    assert len(losers) == 1
    assert str(losers[0]) == "ADMIN khởi tạo đã tồn tại."
    assert len(repository._users) == 1


def test_script_uses_hidden_password_input_and_verifies_login(monkeypatch):
    db = FakeDatabase()
    created = make_user()

    class UserServiceStub:
        calls = []

        def create_initial_admin(self, **values):
            self.calls.append(values)
            return created

    class AuthServiceStub:
        calls = []

        def login(self, username, password):
            self.calls.append((username, password))
            return UserSession(1, username, "First Admin", UserRole.ADMIN)

    user_service = UserServiceStub()
    auth_service = AuthServiceStub()
    answers = iter(["first_admin", "First Admin", "admin@example.com", "0900000000"])
    passwords = iter(["Password@123", "Password@123"])
    output = []
    monkeypatch.setattr(
        "scripts.create_initial_admin.db_settings.DATABASE",
        "student_support_db_test",
    )

    result = run(
        input_fn=lambda prompt: next(answers),
        password_fn=lambda prompt: next(passwords),
        output_fn=output.append,
        services_factory=lambda: (db, user_service, auth_service),
    )

    assert result == 0
    assert db.connection_closed is True
    assert user_service.calls[0]["username"] == "first_admin"
    assert auth_service.calls == [("first_admin", "Password@123")]
    rendered = "\n".join(output)
    assert "student_support_db_test" in rendered
    assert "test database" in rendered
    assert "Password@123" not in rendered
    assert created.password_hash not in rendered


def test_script_does_not_write_when_password_confirmation_differs():
    db = FakeDatabase()

    class NeverCalled:
        def create_initial_admin(self, **values):
            raise AssertionError("create must not be called")

        def login(self, username, password):
            raise AssertionError("login must not be called")

    answers = iter(["first_admin", "First Admin", "", ""])
    passwords = iter(["Password@123", "Different@123"])

    result = run(
        input_fn=lambda prompt: next(answers),
        password_fn=lambda prompt: next(passwords),
        output_fn=lambda message: None,
        services_factory=lambda: (db, NeverCalled(), NeverCalled()),
    )

    assert result == 2


def test_script_reports_when_another_process_finished_bootstrap_first():
    db = FakeDatabase()

    class LosingUserService:
        def create_initial_admin(self, **values):
            raise BusinessRuleError("ADMIN khởi tạo đã tồn tại.")

    class NeverLogin:
        def login(self, username, password):
            raise AssertionError("login must not be called")

    answers = iter(["race_admin_2", "Admin 2", "", ""])
    passwords = iter(["Password@123", "Password@123"])
    output = []

    result = run(
        input_fn=lambda prompt: next(answers),
        password_fn=lambda prompt: next(passwords),
        output_fn=output.append,
        services_factory=lambda: (db, LosingUserService(), NeverLogin()),
    )

    assert result == 3
    rendered = "\n".join(output)
    assert "ADMIN khởi tạo đã tồn tại" in rendered
    assert "sp_getapplock" not in rendered
    assert "Password@123" not in rendered
