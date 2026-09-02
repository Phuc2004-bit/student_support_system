from datetime import date
from decimal import Decimal

import pytest

from config.database import db_settings
from database.connection import DatabaseManager
from exceptions import BusinessRuleError
from models.dto import ScoreCreateData, StudentCreateData
from models.enums import InterventionStatus, UserRole
from repositories import AcademicRepository, SupportRuleRepository, UserRepository
from services import (
    EnrollmentService,
    ScoreService,
    StudentProfileService,
    StudentService,
    SupportService,
)


STUDENT_CODE = "SD7_HS01"
YEAR_NAME = "SD7_2026"
CLASS_NAME = "SD7_10A1"
SUBJECT_CODE = "SD7_M1"
USERNAME = "sd7_teacher"
ASSESSMENT_NAMES = tuple(f"SD7_A{i}" for i in range(1, 8))


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
                 WHERE student_id IN
                 (SELECT student_id FROM dbo.STUDENTS
                  WHERE student_code = ?)))""",
            STUDENT_CODE,
        )
        cursor.execute(
            """DELETE FROM dbo.INTERVENTIONS
               WHERE enrollment_id IN
               (SELECT enrollment_id FROM dbo.STUDENT_ENROLLMENTS
                WHERE student_id IN
                (SELECT student_id FROM dbo.STUDENTS
                 WHERE student_code = ?))""",
            STUDENT_CODE,
        )
        cursor.execute(
            """DELETE FROM dbo.SCORES
               WHERE enrollment_id IN
               (SELECT enrollment_id FROM dbo.STUDENT_ENROLLMENTS
                WHERE student_id IN
                (SELECT student_id FROM dbo.STUDENTS
                 WHERE student_code = ?))""",
            STUDENT_CODE,
        )
        cursor.execute(
            """DELETE FROM dbo.SUPPORT_RULES
               WHERE subject_id IN
               (SELECT subject_id FROM dbo.SUBJECTS
                WHERE subject_code = ?)""",
            SUBJECT_CODE,
        )
        cursor.execute(
            "DELETE FROM dbo.STUDENT_ENROLLMENTS WHERE student_id IN "
            "(SELECT student_id FROM dbo.STUDENTS WHERE student_code = ?)",
            STUDENT_CODE,
        )
        cursor.execute(
            "DELETE FROM dbo.STUDENTS WHERE student_code = ?",
            STUDENT_CODE,
        )
        cursor.execute(
            "DELETE FROM dbo.ASSESSMENTS WHERE assessment_name IN "
            "(?, ?, ?, ?, ?, ?, ?)",
            *ASSESSMENT_NAMES,
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
        cursor.execute(
            "DELETE FROM dbo.USERS WHERE username = ?",
            USERNAME,
        )


def test_detection_batch_support_lifecycle_and_profile_history():
    db = get_test_db()
    academic = AcademicRepository()
    score_service = ScoreService(db)
    support_service = SupportService(db)
    cleanup(db)

    try:
        with db.transaction() as connection:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT grade_id FROM dbo.GRADES WHERE grade_number = ?", 10
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
                connection, SUBJECT_CODE, "Môn detection",
            )
            assessments = [
                academic.create_assessment(
                    connection, subject_id, year_id, name, 1, kind,
                    date(2026, 10, index),
                )
                for index, (name, kind) in enumerate(zip(
                    ASSESSMENT_NAMES,
                    ("QUIZ", "QUIZ", "QUIZ", "QUIZ", "QUIZ", "REVIEW", "QUIZ"),
                ), start=1)
            ]
            SupportRuleRepository().create(
                connection, subject_id, year_id, Decimal("4.00"), True,
            )
            teacher = UserRepository().create(
                connection, USERNAME, "$2b$12$fakehash",
                "Giáo viên detection", UserRole.TEACHER,
            )

        student = StudentService(db).create_student(
            StudentCreateData(STUDENT_CODE, "Học sinh detection")
        )
        enrollment = EnrollmentService(db).enroll_student(
            student.student_id, class_id, date(2026, 9, 1)
        )

        mixed = score_service.create_scores_and_detect((
            ScoreCreateData(enrollment.enrollment_id, assessments[0].assessment_id, Decimal("3.99")),
            ScoreCreateData(enrollment.enrollment_id, assessments[1].assessment_id, Decimal("4.00")),
            ScoreCreateData(enrollment.enrollment_id, assessments[2].assessment_id, Decimal("8.00")),
        ))
        assert len(mixed.scores) == 3
        assert mixed.detected_intervention_count == 1
        first_case = mixed.interventions[0]
        assert first_case.status == InterventionStatus.DETECTED
        assert first_case.trigger_score_id == mixed.scores[0].score_id
        assert score_service.can_edit_score(mixed.scores[0].score_id) is False
        with pytest.raises(BusinessRuleError):
            score_service.update_score(mixed.scores[0].score_id, Decimal("9"))

        support_service.plan_intervention(
            first_case.intervention_id, teacher.user_id,
            date(2026, 10, 4), "Phụ đạo",
        )
        support_service.start_intervention(first_case.intervention_id)

        ordinary_high = score_service.create_scores_and_detect((
            ScoreCreateData(enrollment.enrollment_id, assessments[4].assessment_id, Decimal("9.00")),
        ))
        assert ordinary_high.detected_intervention_count == 0
        assert support_service.get_open_intervention(
            enrollment.enrollment_id, subject_id
        ).status == InterventionStatus.IN_PROGRESS

        support_service.mark_waiting_review(first_case.intervention_id)
        review_batch = score_service.create_scores_and_detect((
            ScoreCreateData(enrollment.enrollment_id, assessments[5].assessment_id, Decimal("7.00")),
        ))
        assert support_service.get_open_intervention(
            enrollment.enrollment_id, subject_id
        ).status == InterventionStatus.WAITING_REVIEW
        completed = support_service.review_intervention(
            first_case.intervention_id, review_batch.scores[0].score_id,
            date(2026, 10, 6),
        )
        assert completed.status == InterventionStatus.COMPLETED

        second_episode = score_service.create_scores_and_detect((
            ScoreCreateData(enrollment.enrollment_id, assessments[6].assessment_id, Decimal("2.90")),
        ))
        assert second_episode.detected_intervention_count == 1
        assert second_episode.interventions[0].intervention_id != first_case.intervention_id
        assert second_episode.interventions[0].status == InterventionStatus.DETECTED

        profile = StudentProfileService(db).get_profile(student.student_id)
        assert len(profile.score_history) == 6
        assert len(profile.intervention_history) == 2
        assert {
            item.status for item in profile.intervention_history
        } == {InterventionStatus.COMPLETED, InterventionStatus.DETECTED}
    finally:
        cleanup(db)
