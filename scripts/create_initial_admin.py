from __future__ import annotations

import getpass
import sys
from collections.abc import Callable
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.database import db_settings  # noqa: E402
from database.connection import DatabaseManager  # noqa: E402
from exceptions import AppError  # noqa: E402
from models.enums import UserRole  # noqa: E402
from services.auth_service import AuthService  # noqa: E402
from services.user_service import UserService  # noqa: E402


InputFunction = Callable[[str], str]
OutputFunction = Callable[[str], None]


def _build_services() -> tuple[DatabaseManager, UserService, AuthService]:
    db = DatabaseManager(db_settings.connection_string())
    return db, UserService(db=db), AuthService(db=db)


def _verify_connection(db: DatabaseManager) -> None:
    connection = db.get_connection()
    connection.close()


def run(
    *,
    input_fn: InputFunction = input,
    password_fn: InputFunction = getpass.getpass,
    output_fn: OutputFunction = print,
    services_factory: Callable[
        [], tuple[DatabaseManager, UserService, AuthService]
    ] = _build_services,
) -> int:
    database_name = db_settings.DATABASE
    output_fn(f"DB_NAME đang sử dụng: {database_name}")
    if database_name.lower() == "student_support_db_test":
        output_fn("CẢNH BÁO: Đây là test database.")

    try:
        db, user_service, auth_service = services_factory()
        _verify_connection(db)
    except AppError as exc:
        output_fn(f"Không thể kết nối database: {exc}")
        return 1

    username = input_fn("Username: ")
    full_name = input_fn("Full name: ")
    email = input_fn("Email: ")
    phone = input_fn("Phone: ")
    password = password_fn("Password: ")
    confirmation = password_fn("Confirm password: ")

    if password != confirmation:
        output_fn("Password và Confirm password không khớp; không tạo tài khoản.")
        return 2

    try:
        created = user_service.create_initial_admin(
            username=username,
            password=password,
            full_name=full_name,
            email=email or None,
            phone=phone or None,
        )
        session = auth_service.login(created.username, password)
    except AppError as exc:
        output_fn(f"Không thể tạo ADMIN khởi tạo: {exc}")
        return 3

    if (
        session.user_id != created.user_id
        or session.role is not UserRole.ADMIN
        or created.role is not UserRole.ADMIN
        or not created.is_active
    ):
        output_fn("Tạo tài khoản xong nhưng xác minh đăng nhập không thành công.")
        return 4

    output_fn(f"Đã tạo và xác minh ADMIN thành công: {created.username}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
