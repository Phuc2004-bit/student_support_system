from enum import Enum


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    TEACHER = "TEACHER"


class StudentStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class EnrollmentStatus(str, Enum):
    ACTIVE = "ACTIVE"
    TRANSFERRED = "TRANSFERRED"
    COMPLETED = "COMPLETED"


class AssessmentStatus(str, Enum):
    ACTIVE = "ACTIVE"
    LOCKED = "LOCKED"
    CANCELLED = "CANCELLED"


class InterventionStatus(str, Enum):
    DETECTED = "DETECTED"
    PLANNED = "PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING_REVIEW = "WAITING_REVIEW"
    CONTINUE = "CONTINUE"
    COMPLETED = "COMPLETED"


class ReviewResult(str, Enum):
    PASSED = "PASSED"
    NOT_PASSED = "NOT_PASSED"