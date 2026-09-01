from datetime import date
from decimal import Decimal

from config.database import db_settings
from database.connection import DatabaseManager
from models.dto import StudentCreateData
from models.enums import InterventionStatus
from repositories import AcademicRepository, InterventionRepository
from services import EnrollmentService, ScoreService, StudentProfileService, StudentService


TEST_CODE = "TEST_PROFILE_001"
TEST_YEAR = "PROF_2026_2027"
TEST_CLASS = "TEST_PROFILE_10A1"
TEST_SUBJECT = "TEST_PROFILE_TOAN"
TEST_ASSESSMENT = "TEST_PROFILE_GK"


def get_test_db() -> DatabaseManager:
    connection_string = db_settings.connection_string().replace(
        "DATABASE=student_support_db;",
        "DATABASE=student_support_db_test;",
    )
    return DatabaseManager(connection_string)


def cleanup(test_db: DatabaseManager) -> None:
    with test_db.transaction() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            DELETE FROM dbo.INTERVENTION_REVIEWS
            WHERE intervention_id IN (
                SELECT i.intervention_id
                FROM dbo.INTERVENTIONS i
                INNER JOIN dbo.STUDENT_ENROLLMENTS e
                    ON e.enrollment_id = i.enrollment_id
                INNER JOIN dbo.STUDENTS s
                    ON s.student_id = e.student_id
                WHERE s.student_code = ?
            )
            """,
            TEST_CODE,
        )
        cursor.execute(
            """
            DELETE FROM dbo.INTERVENTIONS
            WHERE enrollment_id IN (
                SELECT e.enrollment_id
                FROM dbo.STUDENT_ENROLLMENTS e
                INNER JOIN dbo.STUDENTS s
                    ON s.student_id = e.student_id
                WHERE s.student_code = ?
            )
            """,
            TEST_CODE,
        )
        cursor.execute(
            """
            DELETE FROM dbo.SCORES
            WHERE enrollment_id IN (
                SELECT e.enrollment_id
                FROM dbo.STUDENT_ENROLLMENTS e
                INNER JOIN dbo.STUDENTS s
                    ON s.student_id = e.student_id
                WHERE s.student_code = ?
            )
            """,
            TEST_CODE,
        )
        cursor.execute(
            """
            DELETE FROM dbo.STUDENT_ENROLLMENTS
            WHERE student_id IN (
                SELECT student_id FROM dbo.STUDENTS
                WHERE student_code = ?
            )
            """,
            TEST_CODE,
        )
        cursor.execute("DELETE FROM dbo.STUDENTS WHERE student_code = ?", TEST_CODE)
        cursor.execute("DELETE FROM dbo.ASSESSMENTS WHERE assessment_name = ?", TEST_ASSESSMENT)
        cursor.execute("DELETE FROM dbo.CLASSES WHERE class_name = ?", TEST_CLASS)
        cursor.execute("DELETE FROM dbo.SUBJECTS WHERE subject_code = ?", TEST_SUBJECT)
        cursor.execute("DELETE FROM dbo.SCHOOL_YEARS WHERE year_name = ?", TEST_YEAR)


def test_profile_reads_saved_enrollment_score_and_intervention_history():
    test_db = get_test_db()
    academic_repository = AcademicRepository()
    intervention_repository = InterventionRepository()
    student_service = StudentService(test_db)
    enrollment_service = EnrollmentService(test_db)
    score_service = ScoreService(test_db)
    profile_service = StudentProfileService(test_db)

    cleanup(test_db)
    try:
        with test_db.transaction() as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT grade_id FROM dbo.GRADES WHERE grade_number = ?", 10)
            grade = cursor.fetchone()
            if grade is None:
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
                grade_id = grade[0]

            school_year_id = academic_repository.create_school_year(
                connection, TEST_YEAR, date(2026, 9, 1), date(2027, 5, 31)
            )
            class_id = academic_repository.create_class(
                connection, TEST_CLASS, grade_id, school_year_id
            )
            subject_id = academic_repository.create_subject(
                connection, TEST_SUBJECT, "Toán Profile"
            )
            assessment = academic_repository.create_assessment(
                connection, subject_id, school_year_id, TEST_ASSESSMENT,
                1, "MIDTERM", date(2026, 10, 1)
            )

        student = student_service.create_student(
            StudentCreateData(TEST_CODE, "Học sinh Profile")
        )
        enrollment = enrollment_service.enroll_student(
            student.student_id, class_id, date(2026, 9, 1)
        )
        score = score_service.create_score(
            enrollment.enrollment_id, assessment.assessment_id, Decimal("3.00")
        )
        with test_db.transaction() as connection:
            intervention_repository.create(
                connection, enrollment.enrollment_id, subject_id,
                score.score_id, date(2026, 10, 2)
            )

        profile = profile_service.get_profile(student.student_id)

        assert profile.enrollment_history[0].class_name == TEST_CLASS
        assert profile.score_history[0].assessment_name == TEST_ASSESSMENT
        assert profile.score_history[0].score == Decimal("3.00")
        assert profile.intervention_history[0].subject_name == "Toán Profile"
        assert profile.intervention_history[0].status == InterventionStatus.DETECTED
    finally:
        cleanup(test_db)
