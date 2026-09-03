from typing import Protocol

from models.dto import User


class ResponsibleUserServiceContract(Protocol):
    def list_active_teachers(self) -> list[User]:
        ...
