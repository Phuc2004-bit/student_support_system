from typing import Protocol

from models.dto import StudentProfileData


class StudentProfileServiceContract(Protocol):
    def get_profile(
        self,
        student_id: str,
    ) -> StudentProfileData:
        ...
