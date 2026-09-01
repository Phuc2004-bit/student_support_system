from database.connection import DatabaseManager
from exceptions import ValidationError
from models.dto import StudentProfileData
from repositories import (
    EnrollmentRepository,
    InterventionRepository,
    ScoreRepository,
    StudentRepository,
)


class StudentProfileService:
    def __init__(
        self,
        db: DatabaseManager,
        student_repository: StudentRepository | None = None,
        enrollment_repository: EnrollmentRepository | None = None,
        score_repository: ScoreRepository | None = None,
        intervention_repository: InterventionRepository | None = None,
    ) -> None:
        self.db = db
        self.student_repository = student_repository or StudentRepository()
        self.enrollment_repository = enrollment_repository or EnrollmentRepository()
        self.score_repository = score_repository or ScoreRepository()
        self.intervention_repository = (
            intervention_repository or InterventionRepository()
        )

    def get_profile(
        self,
        student_id: str,
    ) -> StudentProfileData:
        if not student_id or not student_id.strip():
            raise ValidationError("student_id không được để trống.")

        with self.db.transaction() as connection:
            student = self.student_repository.get_by_id(
                connection,
                student_id,
            )
            if student is None:
                raise ValidationError("Không tìm thấy học sinh.")

            return StudentProfileData(
                student=student,
                enrollment_history=tuple(
                    self.enrollment_repository.list_by_student(
                        connection,
                        student_id,
                    )
                ),
                score_history=tuple(
                    self.score_repository.list_by_student(
                        connection,
                        student_id,
                    )
                ),
                intervention_history=tuple(
                    self.intervention_repository.list_by_student(
                        connection,
                        student_id,
                    )
                ),
            )
