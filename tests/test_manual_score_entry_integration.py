from datetime import date
from decimal import Decimal

import pytest

from config.database import db_settings
from database.connection import DatabaseManager
from exceptions import DuplicateError
from models.dto import ScoreCreateData, StudentCreateData
from repositories import (
    AcademicRepository,
    EnrollmentRepository,
    ScoreRepository,
    StudentRepository,
)
from services import EnrollmentService, ScoreService


YEAR_NAME = "T103_2627"
CLASS_NAME = "T103_10A"
SUBJECT_CODE = "T103_M1"
STUDENT_CODES = ("T10301", "T10302")
STUDENT_IDS = (
    "t103-student-1",
    "t103-student-2",
)


def get_test_db() -> DatabaseManager:
    connection_string = db_settings.connection_string().replace(
        "DATABASE=student_support_db;",
        "DATABASE=student_support_db_test;",
    )
    assert "student_support_db_test" in connection_string
    return DatabaseManager(connection_string)


def cleanup(db: DatabaseManager) -> None:
    with db.transaction() as connection:
        cursor = connection.cursor()
        placeholders = ", ".join("?" for _ in STUDENT_CODES)

        cursor.execute(
            f"""
            DELETE FROM dbo.INTERVENTIONS
            WHERE enrollment_id IN
            (
                SELECT e.enrollment_id
                FROM dbo.STUDENT_ENROLLMENTS e
                INNER JOIN dbo.STUDENTS s
                    ON s.student_id = e.student_id
                WHERE s.student_code IN ({placeholders})
            )
            """,
            *STUDENT_CODES,
        )
        cursor.execute(
            f"""
            DELETE FROM dbo.SCORES
            WHERE enrollment_id IN
            (
                SELECT e.enrollment_id
                FROM dbo.STUDENT_ENROLLMENTS e
                INNER JOIN dbo.STUDENTS s
                    ON s.student_id = e.student_id
                WHERE s.student_code IN ({placeholders})
            )
            """,
            *STUDENT_CODES,
        )
        cursor.execute(
            f"""
            DELETE FROM dbo.STUDENT_ENROLLMENTS
            WHERE student_id IN
            (
                SELECT student_id
                FROM dbo.STUDENTS
                WHERE student_code IN ({placeholders})
            )
            """,
            *STUDENT_CODES,
        )
        cursor.execute(
            f"""
            DELETE FROM dbo.STUDENTS
            WHERE student_code IN ({placeholders})
            """,
            *STUDENT_CODES,
        )
        cursor.execute(
            """
            DELETE FROM dbo.ASSESSMENTS
            WHERE subject_id IN
            (
                SELECT subject_id
                FROM dbo.SUBJECTS
                WHERE subject_code = ?
            )
            """,
            SUBJECT_CODE,
        )
        cursor.execute(
            "DELETE FROM dbo.SUBJECTS WHERE subject_code = ?",
            SUBJECT_CODE,
        )
        cursor.execute(
            "DELETE FROM dbo.CLASSES WHERE class_name = ?",
            CLASS_NAME,
        )
        cursor.execute(
            "DELETE FROM dbo.SCHOOL_YEARS WHERE year_name = ?",
            YEAR_NAME,
        )


def test_manual_score_roster_and_batch_are_integrated_without_detection():
    db = get_test_db()
    academic_repository = AcademicRepository()
    student_repository = StudentRepository()
    enrollment_repository = EnrollmentRepository()
    score_repository = ScoreRepository()
    cleanup(db)

    try:
        with db.transaction() as connection:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT grade_id FROM dbo.GRADES WHERE grade_number = ?",
                10,
            )
            grade_row = cursor.fetchone()
            if grade_row is None:
                cursor.execute(
                    """
                    INSERT INTO dbo.GRADES (grade_number, grade_name)
                    OUTPUT INSERTED.grade_id
                    VALUES (?, ?)
                    """,
                    10,
                    "Khối 10",
                )
                grade_id = cursor.fetchone()[0]
            else:
                grade_id = grade_row[0]

            school_year_id = academic_repository.create_school_year(
                connection,
                YEAR_NAME,
                date(2026, 9, 1),
                date(2027, 5, 31),
                False,
            )
            class_id = academic_repository.create_class(
                connection,
                CLASS_NAME,
                grade_id,
                school_year_id,
            )
            subject_id = academic_repository.create_subject(
                connection,
                SUBJECT_CODE,
                "Môn T103",
            )
            assessment_ok = academic_repository.create_assessment(
                connection,
                subject_id,
                school_year_id,
                "T103_OK",
                1,
                "TEST",
                date(2026, 10, 1),
            )
            assessment_rollback = academic_repository.create_assessment(
                connection,
                subject_id,
                school_year_id,
                "T103_RB",
                1,
                "TEST",
                date(2026, 10, 2),
            )

            enrollments = []
            for student_id, student_code in zip(
                STUDENT_IDS,
                STUDENT_CODES,
            ):
                student_repository.create(
                    connection,
                    student_id,
                    StudentCreateData(
                        student_code=student_code,
                        full_name=f"HS {student_code}",
                    ),
                )
                enrollments.append(
                    enrollment_repository.create(
                        connection,
                        student_id,
                        class_id,
                        date(2026, 9, 1),
                    )
                )

        roster = EnrollmentService(db).list_class_enrollments(
            class_id,
            school_year_id,
        )
        assert {item.student_code for item in roster} == set(
            STUDENT_CODES
        )

        score_service = ScoreService(db)
        initial_roster = score_service.list_score_roster(
            class_id,
            school_year_id,
            subject_id,
            assessment_ok.assessment_id,
        )
        assert len(initial_roster) == 2
        assert all(item.score_id is None for item in initial_roster)

        created = score_service.create_scores(
            (
                ScoreCreateData(
                    enrollments[0].enrollment_id,
                    assessment_ok.assessment_id,
                    Decimal("6.25"),
                ),
                ScoreCreateData(
                    enrollments[1].enrollment_id,
                    assessment_ok.assessment_id,
                    Decimal("8.00"),
                ),
            )
        )
        assert [score.score for score in created] == [
            Decimal("6.25"),
            Decimal("8.00"),
        ]
        saved_roster = score_service.list_score_roster(
            class_id,
            school_year_id,
            subject_id,
            assessment_ok.assessment_id,
        )
        assert {
            item.enrollment_id: item.score
            for item in saved_roster
        } == {
            enrollments[0].enrollment_id: Decimal("6.25"),
            enrollments[1].enrollment_id: Decimal("8.00"),
        }
        assert all(item.score_id is not None for item in saved_roster)

        score_service.create_score(
            enrollments[1].enrollment_id,
            assessment_rollback.assessment_id,
            Decimal("7.00"),
        )
        with pytest.raises(DuplicateError):
            score_service.create_scores(
                (
                    ScoreCreateData(
                        enrollments[0].enrollment_id,
                        assessment_rollback.assessment_id,
                        Decimal("5.00"),
                    ),
                    ScoreCreateData(
                        enrollments[1].enrollment_id,
                        assessment_rollback.assessment_id,
                        Decimal("9.00"),
                    ),
                )
            )

        with db.transaction() as connection:
            rolled_back = score_repository.get_by_enrollment_assessment(
                connection,
                enrollments[0].enrollment_id,
                assessment_rollback.assessment_id,
            )
            preserved = score_repository.get_by_enrollment_assessment(
                connection,
                enrollments[1].enrollment_id,
                assessment_rollback.assessment_id,
            )
            intervention_count = connection.cursor().execute(
                """
                SELECT COUNT(*)
                FROM dbo.INTERVENTIONS
                WHERE enrollment_id IN (?, ?)
                """,
                enrollments[0].enrollment_id,
                enrollments[1].enrollment_id,
            ).fetchone()[0]
            score_count_before_read = connection.cursor().execute(
                """
                SELECT COUNT(*)
                FROM dbo.SCORES
                WHERE enrollment_id IN (?, ?)
                """,
                enrollments[0].enrollment_id,
                enrollments[1].enrollment_id,
            ).fetchone()[0]

        assert rolled_back is None
        assert preserved is not None
        assert preserved.score == Decimal("7.00")
        assert intervention_count == 0

        refreshed_roster = score_service.list_score_roster(
            class_id,
            school_year_id,
            subject_id,
            assessment_ok.assessment_id,
        )
        assert refreshed_roster == saved_roster
        with db.transaction() as connection:
            score_count_after_read = connection.cursor().execute(
                """
                SELECT COUNT(*)
                FROM dbo.SCORES
                WHERE enrollment_id IN (?, ?)
                """,
                enrollments[0].enrollment_id,
                enrollments[1].enrollment_id,
            ).fetchone()[0]
        assert score_count_after_read == score_count_before_read
    finally:
        cleanup(db)
