from dataclasses import dataclass
from datetime import datetime

from models.enums import UserRole


@dataclass(frozen=True, slots=True)
class User:
    user_id: int
    username: str
    password_hash: str
    full_name: str
    role: UserRole
    email: str | None
    phone: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class UserSession:
    user_id: int
    username: str
    full_name: str
    role: UserRole