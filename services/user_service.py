import re

import bcrypt

from database.connection import DatabaseManager
from exceptions import (
    DuplicateError,
    ValidationError,
)
from models.dto import User
from models.enums import UserRole
from repositories import UserRepository


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
        self._validate_email(email)
        self._validate_phone(phone)

        with self.db.transaction() as connection:

            existing = (
                self.user_repository.get_by_username(
                    connection,
                    username,
                )
            )

            if existing is not None:
                raise DuplicateError(
                    "Tên đăng nhập đã tồn tại."
                )

            password_hash = self._hash_password(
                password
            )

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