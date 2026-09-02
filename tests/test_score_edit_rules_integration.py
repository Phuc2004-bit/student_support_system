from datetime import date
from decimal import Decimal

import pytest

from config.database import db_settings
from database.connection import DatabaseManager
from exceptions import BusinessRuleError
from models.dto import StudentCreateData
from models.enums import InterventionStatus, ReviewResult
from repositories import (
    AcademicRepository,
    EnrollmentRepository,
    InterventionRepository,
    ScoreRepository,
    StudentRepository,
)
from services import ScoreService, StudentProfileService


STUDENT_ID = "score-edit-student"
STUDENT_CODE = "SED_HS01"
YEAR_NAME = "SED_2026"
CLASS_NAME = "SED_10A1"
SUBJECT_CODE = "SED_M1"
ASSESSMENTS = ("SED_TRIGGER", "SED_REVIEW", "SED_FREE")


def get_test_db():
    connection_string = db_settings.connection_string().replace(
        "DATABASE=student_support_db;",
        "DATABASE=student_support_db_test;",
    )
    return DatabaseManager(connection_string)


def cleanup(db):
    with db.transaction() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """DELETE FROM dbo.INTERVENTION_REVIEWS
               WHERE intervention_id IN
               (SELECT intervention_id FROM dbo.INTERVENTIONS
                WHERE enrollment_id IN
                (SELECT enrollment_id FROM dbo.STUDENT_ENROLLMENTS
                 WHERE student_id = ?))""",
            STUDENT_ID,
        )
        cursor.execute(
            """DELETE FROM dbo.INTERVENTIONS
               WHERE enrollment_id IN
               (SELECT enrollment_id FROM dbo.STUDENT_ENROLLMENTS
                WHERE student_id = ?)""",
            STUDENT_ID,
        )
        cursor.execute(
            """DELETE FROM dbo.SCORES
               WHERE enrollment_id IN
               (SELECT enrollment_id FROM dbo.STUDENT_ENROLLMENTS
                WHERE student_id = ?)""",
            STUDENT_ID,
        )
        cursor.execute(
            "DELETE FROM dbo.STUDENT_ENROLLMENTS WHERE student_id = ?",
            STUDENT_ID,
        )
        cursor.execute(
            "DELETE FROM dbo.STUDENTS WHERE student_id = ? OR student_code = ?",
            STUDENT_ID,
            STUDENT_CODE,
        )
        cursor.execute(
            "DELETE FROM dbo.ASSESSMENTS WHERE assessment_name IN (?, ?, ?)",
            *ASSESSMENTS,
        )
        cursor.execute(
            "DELETE FROM dbo.CLASSES WHERE class_name = ?",
            CLASS_NAME,
        )
        cursor.execute(
            "DELETE FROM dbo.SUBJECTS WHERE subject_code = ?",
            SUBJECT_CODE,
        )
        cursor.execute(
            "DELETE FROM dbo.SCHOOL_YEARS WHERE year_name = ?",
            YEAR_NAME,
        )


def test_completed_support_history_locks_trigger_and_review_scores():
    db = get_test_db()
    academic = AcademicRepository()
    students = StudentRepository()
    enrollments = EnrollmentRepository()
    scores = ScoreRepository()
    interventions = InterventionRepository()
    score_service = ScoreService(db)
    profile_service = StudentProfileService(db)
    cleanup(db)

    try:
        with db.transaction() as connection:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT grade_id FROM dbo.GRADES WHERE grade_number = ?",
                10,
            )
            row = cursor.fetchone()
            if row is None:
                cursor.execute(
                    """INSERT INTO dbo.GRADES (grade_number, grade_name)
                       OUTPUT INSERTED.grade_id VALUES (?, ?)""",
                    10,
                    "Khối 10",
                )
                grade_id = cursor.fetchone()[0]
            else:
                grade_id = row[0]

            year_id = academic.create_school_year(
                connection, YEAR_NAME, date(2026, 9, 1),
                date(2027, 5, 31), False,
            )
            class_id = academic.create_class(
                connection, CLASS_NAME, grade_id, year_id,
            )
            subject_id = academic.create_subject(
                connection, SUBJECT_CODE, "Môn edit score",
            )
            assessment_ids = [
                academic.create_assessment(
                    connection, subject_id, year_id, name, 1, kind,
                    date(2026, 10, day),
                ).assessment_id
                for name, kind, day in (
                    (ASSESSMENTS[0], "MIDTERM", 1),
                    (ASSESSMENTS[1], "REVIEW", 2),
                    (ASSESSMENTS[2], "QUIZ", 3),
                )
            ]
            students.create(
                connection,
                STUDENT_ID,
                StudentCreateData(STUDENT_CODE, "Học sinh edit score"),
            )
            enrollment = enrollments.create(
                connection, STUDENT_ID, class_id, date(2026, 9, 1),
            )
            trigger = scores.create(
                connection, enrollment.enrollment_id,
                assessment_ids[0], Decimal("2.50"),
            )
            review = scores.create(
                connection, enrollment.enrollment_id,
                assessment_ids[1], Decimal("4.00"),
            )
            free = scores.create(
                connection, enrollment.enrollment_id,
                assessment_ids[2], Decimal("6.00"),
            )
            intervention = interventions.create(
                connection, enrollment.enrollment_id, subject_id,
                trigger.score_id, date(2026, 10, 1),
            )
            review_item = interventions.create_review(
                connection, intervention.intervention_id, review.score_id,
                date(2026, 10, 2), ReviewResult.PASSED,
            )
            completed = interventions.update_status(
                connection, intervention.intervention_id,
                InterventionStatus.COMPLETED,
            )

        before_intervention = completed
        before_review = review_item

        for locked_score in (trigger, review):
            with pytest.raises(BusinessRuleError):
                score_service.update_score(
                    locked_score.score_id, Decimal("9.00")
                )
            unchanged = score_service.get_score(locked_score.score_id)
            assert unchanged.score == locked_score.score

        updated = score_service.update_score(free.score_id, Decimal("7.25"))
        assert updated.score_id == free.score_id
        assert updated.enrollment_id == free.enrollment_id
        assert updated.assessment_id == free.assessment_id
        assert score_service.get_score(free.score_id).score == Decimal("7.25")

        profile = profile_service.get_profile(STUDENT_ID)
        profile_score = next(
            item for item in profile.score_history
            if item.score_id == free.score_id
        )
        assert profile_score.score == Decimal("7.25")

        with db.transaction() as connection:
            after_intervention = interventions.get_by_id(
                connection, intervention.intervention_id,
            )
            after_review = interventions.list_reviews(
                connection, intervention.intervention_id,
            )[0]
        assert after_intervention == before_intervention
        assert after_review == before_review
    finally:
        cleanup(db)
