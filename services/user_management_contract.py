from typing import Protocol

from models.dto import User, UserListItem, UserSession
from models.enums import UserRole


class UserManagementContract(Protocol):
    def get_own_profile(
        self,
        actor: UserSession,
    ) -> UserListItem: ...

    def update_own_profile(
        self,
        actor: UserSession,
        full_name: str,
        email: str | None = None,
        phone: str | None = None,
    ) -> UserListItem: ...

    def change_own_password(
        self,
        actor: UserSession,
        current_password: str,
        new_password: str,
    ) -> UserListItem: ...

    def admin_list_users(
        self,
        actor: UserSession,
        search: str | None = None,
    ) -> list[UserListItem]: ...

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
    ) -> User: ...

    def admin_update_user(
        self,
        actor: UserSession,
        user_id: int,
        full_name: str,
        role: UserRole,
        email: str | None = None,
        phone: str | None = None,
    ) -> User: ...

    def admin_set_user_active(
        self,
        actor: UserSession,
        user_id: int,
        is_active: bool,
    ) -> User: ...
