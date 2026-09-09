import re

import bcrypt
import pyodbc

from database.connection import DatabaseManager
from exceptions import (
    BusinessRuleError,
    DatabaseError,
    DuplicateError,
    ValidationError,
)
from models.dto import User, UserListItem, UserSession
from models.enums import UserRole
from repositories import UserRepository
from services.permission_service import PermissionService


class UserService:
    def __init__(
        self,
        db: DatabaseManager,
        user_repository: UserRepository | None = None,
    ):
        self.db = db
        self.user_repository = (
            user_repository
            or UserRepository()
        )

    # =====================================================
    # CREATE
    # =====================================================

    def create_user(
        self,
        username: str,
        password: str,
        full_name: str,
        role: UserRole,
        email: str | None = None,
        phone: str | None = None,
        is_active: bool = True,
    ) -> User:
        """
        Tạo tài khoản người dùng mới.

        Password plaintext chỉ tồn tại ở Service trong thời gian xử lý.
        Database chỉ lưu password_hash.
        """

        username = self._normalize_username(username)
        full_name = self._normalize_full_name(full_name)
        email = self._normalize_optional(email)
        phone = self._normalize_optional(phone)

        self._validate_password(password)
        self._validate_role(role)
        if not isinstance(is_active, bool):
            raise ValidationError(
                "Trạng thái hoạt động không hợp lệ."
            )
        self._validate_email(email)
        self._validate_phone(phone)

        try:
            with self.db.transaction() as connection:
                existing = self.user_repository.get_by_username(
                    connection,
                    username,
                )
                if existing is not None:
                    raise DuplicateError(
                        "Tên đăng nhập đã tồn tại."
                    )
                password_hash = self._hash_password(password)
                return self.user_repository.create(
                    connection=connection,
                    username=username,
                    password_hash=password_hash,
                    full_name=full_name,
                    role=role,
                    email=email,
                    phone=phone,
                    is_active=is_active,
                )
        except pyodbc.IntegrityError as exc:
            raise DuplicateError("Tên đăng nhập đã tồn tại.") from exc
        except pyodbc.Error as exc:
            raise DatabaseError("Không thể tạo người dùng.") from exc

    def create_initial_admin(
        self,
        username: str,
        password: str,
        full_name: str,
        email: str | None = None,
        phone: str | None = None,
    ) -> User:
        """Create the first active ADMIN account atomically.

        This bootstrap-only API refuses to create an account when an active
        ADMIN already exists. Validation, password hashing, and the transaction
        remain owned by the service layer.
        """

        username = self._normalize_username(username)
        full_name = self._normalize_full_name(full_name)
        email = self._normalize_optional(email)
        phone = self._normalize_optional(phone)

        self._validate_password(password)
        self._validate_email(email)
        self._validate_phone(phone)

        try:
            with self.db.transaction() as connection:
                lock_result = (
                    self.user_repository
                    .acquire_initial_admin_bootstrap_lock(connection)
                )
                if lock_result < 0:
                    raise DatabaseError(
                        "Không thể khóa thao tác tạo ADMIN khởi tạo."
                    )

                existing = self.user_repository.get_by_username(
                    connection,
                    username,
                )
                if existing is not None:
                    raise DuplicateError("Tên đăng nhập đã tồn tại.")
                if self.user_repository.count_active_admins(connection) > 0:
                    raise BusinessRuleError(
                        "ADMIN khởi tạo đã tồn tại."
                    )

                password_hash = self._hash_password(password)
                return self.user_repository.create(
                    connection=connection,
                    username=username,
                    password_hash=password_hash,
                    full_name=full_name,
                    role=UserRole.ADMIN,
                    email=email,
                    phone=phone,
                    is_active=True,
                )
        except pyodbc.IntegrityError as exc:
            raise DuplicateError("Tên đăng nhập đã tồn tại.") from exc
        except pyodbc.Error as exc:
            raise DatabaseError("Không thể tạo ADMIN khởi tạo.") from exc

    # =====================================================
    # READ
    # =====================================================

    def get_user(
        self,
        user_id: int,
    ) -> User:
        if user_id <= 0:
            raise ValidationError(
                "user_id không hợp lệ."
            )

        with self.db.transaction() as connection:
            user = self.user_repository.get_by_id(
                connection,
                user_id,
            )

            if user is None:
                raise ValidationError(
                    "Không tìm thấy người dùng."
                )

            return user

    def get_by_username(
        self,
        username: str,
    ) -> User | None:
        username = self._normalize_username(
            username
        )

        with self.db.transaction() as connection:
            return (
                self.user_repository
                .get_by_username(
                    connection,
                    username,
                )
            )

    def list_users(
        self,
    ) -> list[User]:
        with self.db.transaction() as connection:
            return self.user_repository.list_all(
                connection
            )

    def list_active_teachers(self) -> list[User]:
        with self.db.transaction() as connection:
            return self.user_repository.list_active_teachers(
                connection
            )

    # =====================================================
    # CURRENT ACCOUNT
    # =====================================================

    def get_own_profile(
        self,
        actor: UserSession,
    ) -> UserListItem:
        PermissionService.require_teacher_or_admin(actor)
        try:
            with self.db.transaction() as connection:
                profile = self.user_repository.get_profile_by_id(
                    connection,
                    actor.user_id,
                )
                self._validate_session_identity(actor, profile)
                return profile
        except pyodbc.Error as exc:
            raise DatabaseError("Không thể tải hồ sơ tài khoản.") from exc

    def update_own_profile(
        self,
        actor: UserSession,
        full_name: str,
        email: str | None = None,
        phone: str | None = None,
    ) -> UserListItem:
        PermissionService.require_teacher_or_admin(actor)
        full_name = self._normalize_full_name(full_name)
        email = self._normalize_optional(email)
        phone = self._normalize_optional(phone)
        self._validate_email(email)
        self._validate_phone(phone)
        try:
            with self.db.transaction() as connection:
                existing = self.user_repository.get_profile_by_id(
                    connection,
                    actor.user_id,
                )
                self._validate_session_identity(actor, existing)
                updated = self.user_repository.update_profile(
                    connection,
                    actor.user_id,
                    full_name,
                    email,
                    phone,
                )
                if updated is None:
                    raise ValidationError("Không thể cập nhật hồ sơ tài khoản.")
                return self._to_list_item(updated)
        except pyodbc.Error as exc:
            raise DatabaseError("Không thể cập nhật hồ sơ tài khoản.") from exc

    def change_own_password(
        self,
        actor: UserSession,
        current_password: str,
        new_password: str,
    ) -> UserListItem:
        PermissionService.require_teacher_or_admin(actor)
        if not isinstance(current_password, str) or not current_password:
            raise ValidationError("Mật khẩu hiện tại không đúng.")
        self._validate_password(new_password)
        try:
            with self.db.transaction() as connection:
                existing = self.user_repository.get_by_id(
                    connection,
                    actor.user_id,
                )
                self._validate_session_identity(actor, existing)
                if not self.verify_password(current_password, existing.password_hash):
                    raise ValidationError("Mật khẩu hiện tại không đúng.")
                if self.verify_password(new_password, existing.password_hash):
                    raise BusinessRuleError(
                        "Mật khẩu mới phải khác mật khẩu hiện tại."
                    )
                password_hash = self._hash_password(new_password)
                updated = self.user_repository.update_password_hash(
                    connection,
                    actor.user_id,
                    password_hash,
                )
                if updated is None:
                    raise ValidationError("Không thể đổi mật khẩu.")
                return self._to_list_item(updated)
        except pyodbc.Error as exc:
            raise DatabaseError("Không thể đổi mật khẩu.") from exc

    # =====================================================
    # ADMIN MANAGEMENT
    # =====================================================

    def admin_list_users(
        self,
        actor: UserSession,
        search: str | None = None,
    ) -> list[UserListItem]:
        PermissionService.require_manage_users(actor)
        if search is not None and not isinstance(search, str):
            raise ValidationError("Từ khóa tìm kiếm không hợp lệ.")
        normalized_search = search.strip() if search else None
        with self.db.transaction() as connection:
            return self.user_repository.list_for_management(
                connection,
                normalized_search or None,
            )

    def admin_create_user(
        self,
        actor: UserSession,
        username: str,
        password: str,
        full_name: str,
        role: UserRole,
        email: str | None = None,
        phone: str | None = None,
        is_active: bool = True,
    ) -> User:
        PermissionService.require_manage_users(actor)
        return self.create_user(
            username,
            password,
            full_name,
            role,
            email,
            phone,
            is_active,
        )

    def admin_update_user(
        self,
        actor: UserSession,
        user_id: int,
        full_name: str,
        role: UserRole,
        email: str | None = None,
        phone: str | None = None,
    ) -> User:
        PermissionService.require_manage_users(actor)
        self._validate_user_id(user_id)
        full_name = self._normalize_full_name(full_name)
        email = self._normalize_optional(email)
        phone = self._normalize_optional(phone)
        self._validate_role(role)
        self._validate_email(email)
        self._validate_phone(phone)
        try:
            with self.db.transaction() as connection:
                existing = self.user_repository.get_by_id(connection, user_id)
                if existing is None:
                    raise ValidationError("Không tìm thấy người dùng.")
                if existing.role == UserRole.ADMIN and role != UserRole.ADMIN:
                    if actor.user_id == user_id:
                        raise BusinessRuleError(
                            "Không thể tự hạ quyền tài khoản đang đăng nhập."
                        )
                    if (
                        existing.is_active
                        and self.user_repository.count_active_admins(connection) <= 1
                    ):
                        raise BusinessRuleError(
                            "Hệ thống phải còn ít nhất một ADMIN đang hoạt động."
                        )
                updated = self.user_repository.update_management_details(
                    connection,
                    user_id,
                    full_name,
                    role,
                    email,
                    phone,
                )
                if updated is None:
                    raise ValidationError("Không thể cập nhật người dùng.")
                return updated
        except pyodbc.Error as exc:
            raise DatabaseError("Không thể cập nhật người dùng.") from exc

    def admin_set_user_active(
        self,
        actor: UserSession,
        user_id: int,
        is_active: bool,
    ) -> User:
        PermissionService.require_manage_users(actor)
        self._validate_user_id(user_id)
        if not isinstance(is_active, bool):
            raise ValidationError("Trạng thái hoạt động không hợp lệ.")
        try:
            with self.db.transaction() as connection:
                existing = self.user_repository.get_by_id(connection, user_id)
                if existing is None:
                    raise ValidationError("Không tìm thấy người dùng.")
                if not is_active:
                    if actor.user_id == user_id:
                        raise BusinessRuleError(
                            "Không thể vô hiệu hóa tài khoản đang đăng nhập."
                        )
                    if (
                        existing.role == UserRole.ADMIN
                        and existing.is_active
                        and self.user_repository.count_active_admins(connection) <= 1
                    ):
                        raise BusinessRuleError(
                            "Hệ thống phải còn ít nhất một ADMIN đang hoạt động."
                        )
                updated = self.user_repository.set_active(
                    connection,
                    user_id,
                    is_active,
                )
                if updated is None:
                    raise ValidationError("Không thể cập nhật người dùng.")
                return updated
        except pyodbc.Error as exc:
            raise DatabaseError("Không thể cập nhật người dùng.") from exc

    # =====================================================
    # UPDATE PROFILE
    # =====================================================

    def update_profile(
        self,
        user_id: int,
        full_name: str,
        email: str | None = None,
        phone: str | None = None,
    ) -> User:
        if user_id <= 0:
            raise ValidationError(
                "user_id không hợp lệ."
            )

        full_name = self._normalize_full_name(
            full_name
        )

        email = self._normalize_optional(
            email
        )

        phone = self._normalize_optional(
            phone
        )

        self._validate_email(email)
        self._validate_phone(phone)

        with self.db.transaction() as connection:

            existing = self.user_repository.get_by_id(
                connection,
                user_id,
            )

            if existing is None:
                raise ValidationError(
                    "Không tìm thấy người dùng."
                )

            updated = (
                self.user_repository.update_profile(
                    connection,
                    user_id,
                    full_name,
                    email,
                    phone,
                )
            )

            if updated is None:
                raise ValidationError(
                    "Không thể cập nhật người dùng."
                )

            return updated

    # =====================================================
    # ACTIVE / DISABLE
    # =====================================================

    def set_active(
        self,
        user_id: int,
        is_active: bool,
    ) -> User:
        if user_id <= 0:
            raise ValidationError(
                "user_id không hợp lệ."
            )

        if not isinstance(is_active, bool):
            raise ValidationError(
                "Trạng thái hoạt động không hợp lệ."
            )

        with self.db.transaction() as connection:

            existing = self.user_repository.get_by_id(
                connection,
                user_id,
            )

            if existing is None:
                raise ValidationError(
                    "Không tìm thấy người dùng."
                )

            updated = self.user_repository.set_active(
                connection,
                user_id,
                is_active,
            )

            if updated is None:
                raise ValidationError(
                    "Không thể cập nhật trạng thái "
                    "người dùng."
                )

            return updated

    # =====================================================
    # PASSWORD
    # =====================================================

    def reset_password(
        self,
        user_id: int,
        new_password: str,
    ) -> User:
        """
        Đặt mật khẩu mới.

        Method này chưa kiểm tra mật khẩu cũ.
        Việc xác thực người đang đăng nhập sẽ được xử lý
        ở AuthService / PermissionService.
        """

        if user_id <= 0:
            raise ValidationError(
                "user_id không hợp lệ."
            )

        self._validate_password(
            new_password
        )

        with self.db.transaction() as connection:

            existing = self.user_repository.get_by_id(
                connection,
                user_id,
            )

            if existing is None:
                raise ValidationError(
                    "Không tìm thấy người dùng."
                )

            password_hash = self._hash_password(
                new_password
            )

            updated = (
                self.user_repository
                .update_password_hash(
                    connection,
                    user_id,
                    password_hash,
                )
            )

            if updated is None:
                raise ValidationError(
                    "Không thể cập nhật mật khẩu."
                )

            return updated

    # =====================================================
    # PASSWORD UTILITIES
    # =====================================================

    @staticmethod
    def _hash_password(
        password: str,
    ) -> str:
        """
        Hash password bằng bcrypt.

        Database chỉ lưu chuỗi hash.
        """
        hashed = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt(rounds=12),
        )

        return hashed.decode("utf-8")

    @staticmethod
    def verify_password(
        password: str,
        password_hash: str,
    ) -> bool:
        """
        Kiểm tra plaintext password với bcrypt hash.

        Method này sẽ được AuthService sử dụng.
        """

        if not password:
            return False

        if not password_hash:
            return False

        try:
            return bcrypt.checkpw(
                password.encode("utf-8"),
                password_hash.encode("utf-8"),
            )

        except (ValueError, TypeError):
            return False

    # =====================================================
    # VALIDATION
    # =====================================================

    @staticmethod
    def _validate_user_id(user_id: int) -> None:
        if (
            isinstance(user_id, bool)
            or not isinstance(user_id, int)
            or user_id <= 0
        ):
            raise ValidationError("user_id không hợp lệ.")

    @staticmethod
    def _validate_session_identity(
        actor: UserSession,
        user: User | UserListItem | None,
    ) -> None:
        if (
            user is None
            or user.username != actor.username
            or user.role != actor.role
        ):
            raise ValidationError("Phiên đăng nhập không còn hợp lệ.")
        if not user.is_active:
            raise ValidationError("Tài khoản đã bị vô hiệu hóa.")

    @staticmethod
    def _to_list_item(user: User) -> UserListItem:
        return UserListItem(
            user_id=user.user_id,
            username=user.username,
            full_name=user.full_name,
            role=user.role,
            email=user.email,
            phone=user.phone,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    @staticmethod
    def _normalize_username(
        username: str,
    ) -> str:
        if username is None:
            raise ValidationError(
                "Tên đăng nhập không được để trống."
            )

        username = username.strip().lower()

        if not username:
            raise ValidationError(
                "Tên đăng nhập không được để trống."
            )

        if len(username) < 3:
            raise ValidationError(
                "Tên đăng nhập phải có ít nhất "
                "3 ký tự."
            )

        if len(username) > 50:
            raise ValidationError(
                "Tên đăng nhập không được vượt quá "
                "50 ký tự."
            )

        if not re.fullmatch(
            r"[a-z0-9._-]+",
            username,
        ):
            raise ValidationError(
                "Tên đăng nhập chỉ được chứa "
                "chữ cái không dấu, số, dấu chấm, "
                "gạch dưới hoặc gạch ngang."
            )

        return username

    @staticmethod
    def _normalize_full_name(
        full_name: str,
    ) -> str:
        if full_name is None:
            raise ValidationError(
                "Họ tên không được để trống."
            )

        full_name = full_name.strip()

        if not full_name:
            raise ValidationError(
                "Họ tên không được để trống."
            )

        if len(full_name) > 100:
            raise ValidationError(
                "Họ tên không được vượt quá "
                "100 ký tự."
            )

        return full_name

    @staticmethod
    def _normalize_optional(
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        value = value.strip()

        return value or None

    @staticmethod
    def _validate_password(
        password: str,
    ) -> None:
        if password is None:
            raise ValidationError(
                "Mật khẩu không được để trống."
            )

        if len(password) < 8:
            raise ValidationError(
                "Mật khẩu phải có ít nhất "
                "8 ký tự."
            )

        if len(password) > 72:
            raise ValidationError(
                "Mật khẩu không được vượt quá "
                "72 ký tự."
            )

    @staticmethod
    def _validate_role(
        role: UserRole,
    ) -> None:
        if not isinstance(role, UserRole):
            raise ValidationError(
                "Vai trò người dùng không hợp lệ."
            )

    @staticmethod
    def _validate_email(
        email: str | None,
    ) -> None:
        if email is None:
            return

        if len(email) > 100:
            raise ValidationError(
                "Email không được vượt quá "
                "100 ký tự."
            )

        pattern = (
            r"^[A-Za-z0-9._%+-]+"
            r"@[A-Za-z0-9.-]+"
            r"\.[A-Za-z]{2,}$"
        )

        if not re.fullmatch(
            pattern,
            email,
        ):
            raise ValidationError(
                "Email không hợp lệ."
            )

    @staticmethod
    def _validate_phone(
        phone: str | None,
    ) -> None:
        if phone is None:
            return

        if len(phone) > 20:
            raise ValidationError(
                "Số điện thoại không được vượt quá "
                "20 ký tự."
            )

        cleaned = (
            phone.replace(" ", "")
            .replace("-", "")
        )

        if cleaned.startswith("+"):
            number_part = cleaned[1:]
        else:
            number_part = cleaned

        if not number_part.isdigit():
            raise ValidationError(
                "Số điện thoại không hợp lệ."
            )

        if len(number_part) < 9:
            raise ValidationError(
                "Số điện thoại quá ngắn."
            )
