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
    if database_name.casefold() == "student_support_db_test":
        output_fn("CẢNH BÁO: Đây là test database.")

    try:
        db, user_service, auth_service = services_factory()
        _verify_connection(db)
    except AppError as exc:
        output_fn(f"Không thể kết nối database: {exc}")
        return 1

    username = input_fn("Username [admin]: ").strip() or "admin"
    try:
        existing = user_service.get_by_username(username)
    except AppError as exc:
        output_fn(f"Không thể kiểm tra tài khoản: {exc}")
        return 2

    if existing is None:
        output_fn("Không tìm thấy tài khoản; mật khẩu không được thay đổi.")
        return 3
    if existing.role is not UserRole.ADMIN:
        output_fn("Tài khoản không có role ADMIN; mật khẩu không được thay đổi.")
        return 4
    if not existing.is_active:
        output_fn("Tài khoản ADMIN đang bị vô hiệu hóa; mật khẩu không được thay đổi.")
        return 5

    new_password = password_fn("New password: ")
    confirmation = password_fn("Confirm password: ")
    if new_password != confirmation:
        output_fn("New password và Confirm password không khớp; không có thay đổi.")
        return 6

    try:
        updated = user_service.reset_admin_password(username, new_password)
        session = auth_service.login(updated.username, new_password)
    except AppError as exc:
        output_fn(f"Không thể reset mật khẩu ADMIN: {exc}")
        return 7

    unchanged_identity = (
        updated.user_id == existing.user_id
        and updated.username == existing.username
        and updated.full_name == existing.full_name
        and updated.role is existing.role is UserRole.ADMIN
        and updated.email == existing.email
        and updated.phone == existing.phone
        and updated.is_active == existing.is_active
    )
    verified = (
        session.user_id == updated.user_id
        and session.username == updated.username
        and session.role is UserRole.ADMIN
        and updated.is_active
        and unchanged_identity
    )
    if not verified:
        output_fn("Mật khẩu đã được cập nhật nhưng xác minh tài khoản không thành công.")
        return 8

    output_fn(f"Đã reset và xác minh đăng nhập ADMIN thành công: {updated.username}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
