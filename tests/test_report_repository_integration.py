from datetime import date
from decimal import Decimal

from config.database import db_settings
from database.connection import DatabaseManager
from models.dto import StudentCreateData
from repositories import (
    AcademicRepository,
    EnrollmentRepository,
    InterventionRepository,
    ScoreRepository,
    StudentRepository,
)
from repositories.report_repository import ReportRepository


TEST_YEAR = "TRPT_2026_2027"
TEST_CLASS = "TRPT_10A1"
TEST_SUBJECT = "TRPT_TOAN"
TEST_ASSESSMENT_1 = "TRPT_ASSESSMENT_1"
TEST_ASSESSMENT_2 = "TRPT_ASSESSMENT_2"
TEST_ASSESSMENT_3 = "TRPT_ASSESSMENT_3"
TEST_CODES = ("TRPT_HS001", "TRPT_HS002")


def get_test_db() -> DatabaseManager:
    connection_string = (
        db_settings.connection_string()
        .replace(
            "DATABASE=student_support_db;",
            "DATABASE=student_support_db_test;",
        )
    )
    return DatabaseManager(connection_string)


def cleanup(test_db: DatabaseManager) -> None:
    with test_db.transaction() as connection:
        cursor = connection.cursor()

        cursor.execute(
            """
            DELETE FROM dbo.INTERVENTION_REVIEWS
            WHERE intervention_id IN
            (
                SELECT i.intervention_id
                FROM dbo.INTERVENTIONS i
                JOIN dbo.STUDENT_ENROLLMENTS e
                  ON e.enrollment_id = i.enrollment_id
                JOIN dbo.STUDENTS s
                  ON s.student_id = e.student_id
                WHERE s.student_code IN (?, ?)
            )
            """,
            *TEST_CODES,
        )

        cursor.execute(
            """
            DELETE FROM dbo.INTERVENTIONS
            WHERE enrollment_id IN
            (
                SELECT e.enrollment_id
                FROM dbo.STUDENT_ENROLLMENTS e
                JOIN dbo.STUDENTS s
                  ON s.student_id = e.student_id
                WHERE s.student_code IN (?, ?)
            )
            """,
            *TEST_CODES,
        )

        cursor.execute(
            """
            DELETE FROM dbo.SCORES
            WHERE enrollment_id IN
            (
                SELECT e.enrollment_id
                FROM dbo.STUDENT_ENROLLMENTS e
                JOIN dbo.STUDENTS s
                  ON s.student_id = e.student_id
                WHERE s.student_code IN (?, ?)
            )
            """,
            *TEST_CODES,
        )

        cursor.execute(
            """
            DELETE FROM dbo.ASSESSMENTS
            WHERE assessment_name IN (?, ?, ?)
            """,
            TEST_ASSESSMENT_1,
            TEST_ASSESSMENT_2,
            TEST_ASSESSMENT_3,
        )

        cursor.execute(
            """
            DELETE FROM dbo.STUDENT_ENROLLMENTS
            WHERE student_id IN
            (
                SELECT student_id
                FROM dbo.STUDENTS
                WHERE student_code IN (?, ?)
            )
            """,
            *TEST_CODES,
        )

        cursor.execute(
            """
            DELETE FROM dbo.STUDENTS
            WHERE student_code IN (?, ?)
            """,
            *TEST_CODES,
        )

        cursor.execute(
            "DELETE FROM dbo.CLASSES WHERE class_name = ?",
            TEST_CLASS,
        )

        cursor.execute(
            "DELETE FROM dbo.SUBJECTS WHERE subject_code = ?",
            TEST_SUBJECT,
        )

        cursor.execute(
            "DELETE FROM dbo.SCHOOL_YEARS WHERE year_name = ?",
            TEST_YEAR,
        )


def seed_report_data(test_db: DatabaseManager):
    academic_repo = AcademicRepository()
    student_repo = StudentRepository()
    enrollment_repo = EnrollmentRepository()
    score_repo = ScoreRepository()
    intervention_repo = InterventionRepository()

    with test_db.transaction() as connection:
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

        school_year_id = academic_repo.create_school_year(
            connection,
            TEST_YEAR,
            date(2026, 9, 7),
            date(2027, 5, 31),
            False,
        )

        class_id = academic_repo.create_class(
            connection,
            TEST_CLASS,
            grade_id,
            school_year_id,
        )

        subject_id = academic_repo.create_subject(
            connection,
            TEST_SUBJECT,
            "Toán Report Test",
        )

        a1 = academic_repo.create_assessment(
            connection,
            subject_id,
            school_year_id,
            TEST_ASSESSMENT_1,
            1,
            "MIDTERM",
            date(2026, 10, 10),
        )
        a2 = academic_repo.create_assessment(
            connection,
            subject_id,
            school_year_id,
            TEST_ASSESSMENT_2,
            1,
            "REVIEW",
            date(2026, 11, 1),
        )
        a3 = academic_repo.create_assessment(
            connection,
            subject_id,
            school_year_id,
            TEST_ASSESSMENT_3,
            1,
            "REVIEW",
            date(2026, 11, 20),
        )

        enrollment_ids = []

        for idx, code in enumerate(TEST_CODES, start=1):
            student_id = f"trpt-student-{idx}"

            student_repo.create(
                connection,
                student_id,
                StudentCreateData(
                    student_code=code,
                    full_name=f"Học sinh Report {idx}",
                ),
            )

            enrollment = enrollment_repo.create(
                connection,
                student_id,
                class_id,
                date(2026, 9, 7),
            )
            enrollment_ids.append(enrollment.enrollment_id)

        # HS001: COMPLETED với 2 review, latest phải là PASSED 4.20
        trigger_1 = score_repo.create(
            connection,
            enrollment_ids[0],
            a1.assessment_id,
            Decimal("2.80"),
        )
        i1 = intervention_repo.create(
            connection,
            enrollment_ids[0],
            subject_id,
            trigger_1.score_id,
            date(2026, 10, 10),
        )

        review_score_1 = score_repo.create(
            connection,
            enrollment_ids[0],
            a2.assessment_id,
            Decimal("3.20"),
        )
        cursor.execute(
            """
            INSERT INTO dbo.INTERVENTION_REVIEWS
            (
                intervention_id,
                score_id,
                review_date,
                result,
                notes,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, GETDATE())
            """,
            i1.intervention_id,
            review_score_1.score_id,
            date(2026, 11, 1),
            "NOT_PASSED",
            "Lần 1",
        )

        review_score_2 = score_repo.create(
            connection,
            enrollment_ids[0],
            a3.assessment_id,
            Decimal("4.20"),
        )
        cursor.execute(
            """
            INSERT INTO dbo.INTERVENTION_REVIEWS
            (
                intervention_id,
                score_id,
                review_date,
                result,
                notes,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, GETDATE())
            """,
            i1.intervention_id,
            review_score_2.score_id,
            date(2026, 11, 20),
            "PASSED",
            "Lần 2",
        )
        cursor.execute(
            """
            UPDATE dbo.INTERVENTIONS
            SET status = ?, updated_at = GETDATE()
            WHERE intervention_id = ?
            """,
            "COMPLETED",
            i1.intervention_id,
        )

        # HS002: DETECTED, chưa có review.
        trigger_2 = score_repo.create(
            connection,
            enrollment_ids[1],
            a1.assessment_id,
            Decimal("2.50"),
        )
        i2 = intervention_repo.create(
            connection,
            enrollment_ids[1],
            subject_id,
            trigger_2.score_id,
            date(2026, 10, 10),
        )

    return {
        "school_year_id": school_year_id,
        "grade_id": grade_id,
        "class_id": class_id,
        "subject_id": subject_id,
        "completed_intervention_id": i1.intervention_id,
        "detected_intervention_id": i2.intervention_id,
    }


def test_list_support_cases_uses_latest_review():
    test_db = get_test_db()
    cleanup(test_db)

    try:
        seeded = seed_report_data(test_db)
        repo = ReportRepository()

        with test_db.transaction() as connection:
            rows = repo.list_support_cases(
                connection,
                seeded["school_year_id"],
            )

        assert len(rows) == 2

        completed = next(
            row for row in rows
            if row.intervention_id
            == seeded["completed_intervention_id"]
        )

        assert completed.status == "COMPLETED"
        assert completed.trigger_score == Decimal("2.80")
        assert completed.latest_review_date == date(2026, 11, 20)
        assert completed.latest_review_score == Decimal("4.20")
        assert completed.latest_review_result == "PASSED"

        detected = next(
            row for row in rows
            if row.intervention_id
            == seeded["detected_intervention_id"]
        )

        assert detected.status == "DETECTED"
        assert detected.latest_review_date is None
        assert detected.latest_review_score is None
        assert detected.latest_review_result is None
    finally:
        cleanup(test_db)


def test_support_summary_and_filters():
    test_db = get_test_db()
    cleanup(test_db)

    try:
        seeded = seed_report_data(test_db)
        repo = ReportRepository()

        with test_db.transaction() as connection:
            summary = repo.get_support_summary(
                connection,
                seeded["school_year_id"],
                grade_id=seeded["grade_id"],
                class_id=seeded["class_id"],
                subject_id=seeded["subject_id"],
            )

            completed_rows = repo.list_support_cases(
                connection,
                seeded["school_year_id"],
                subject_id=seeded["subject_id"],
                status="COMPLETED",
            )

        assert summary.total_cases == 2
        assert summary.completed_count == 1
        assert summary.detected_count == 1
        assert summary.planned_count == 0
        assert summary.in_progress_count == 0
        assert summary.waiting_review_count == 0
        assert summary.continue_count == 0

        assert len(completed_rows) == 1
        assert completed_rows[0].status == "COMPLETED"
    finally:
        cleanup(test_db)
