from database.connection import DatabaseManager
from exceptions import ValidationError
from models.dto import UserSession
from repositories import UserRepository
from services.user_service import UserService


class AuthService:
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
    # LOGIN
    # =====================================================

    def login(
        self,
        username: str,
        password: str,
    ) -> UserSession:
        """
        Xác thực tài khoản và trả về UserSession.

        Không trả password_hash ra UI.
        """

        username = self._normalize_username(
            username
        )

        if password is None or not password:
            raise ValidationError(
                "Mật khẩu không được để trống."
            )

        with self.db.transaction() as connection:

            user = self.user_repository.get_by_username(
                connection,
                username,
            )

            if user is None:
                raise ValidationError(
                    "Tên đăng nhập hoặc mật khẩu không đúng."
                )

            if not user.is_active:
                raise ValidationError(
                    "Tài khoản đã bị vô hiệu hóa."
                )

            password_ok = UserService.verify_password(
                password,
                user.password_hash,
            )

            if not password_ok:
                raise ValidationError(
                    "Tên đăng nhập hoặc mật khẩu không đúng."
                )

            return UserSession(
                user_id=user.user_id,
                username=user.username,
                full_name=user.full_name,
                role=user.role,
            )

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

        return username