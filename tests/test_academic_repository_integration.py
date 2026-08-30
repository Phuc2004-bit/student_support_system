from datetime import date

from config.database import db_settings
from database.connection import DatabaseManager
from models.enums import AssessmentStatus
from repositories import AcademicRepository


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
            DELETE FROM dbo.ASSESSMENTS
            WHERE assessment_name = N'TEST_ASSESSMENT'
            """
        )

        cursor.execute(
            """
            DELETE FROM dbo.CLASSES
            WHERE class_name = N'TEST_10A2'
            """
        )

        cursor.execute(
            """
            DELETE FROM dbo.SUBJECTS
            WHERE subject_code = 'TEST_TOAN'
            """
        )

        cursor.execute(
            """
            DELETE FROM dbo.SCHOOL_YEARS
            WHERE year_name = 'TEST_2027_2028'
            """
        )

        cursor.execute(
            """
            DELETE FROM dbo.GRADES
            WHERE grade_number = 10
              AND grade_name = N'TEST_GRADE_10'
            """
        )


def test_academic_repository_flow():
    test_db = get_test_db()
    repo = AcademicRepository()

    cleanup(test_db)

    with test_db.transaction() as connection:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO dbo.GRADES
            (
                grade_number,
                grade_name
            )
            OUTPUT INSERTED.grade_id
            VALUES (?, ?)
            """,
            10,
            "TEST_GRADE_10",
        )

        grade_id = cursor.fetchone()[0]

        school_year_id = repo.create_school_year(
            connection,
            "TEST_2027_2028",
            date(2027, 9, 1),
            date(2028, 5, 31),
            False,
        )

        class_id = repo.create_class(
            connection,
            "TEST_10A2",
            grade_id,
            school_year_id,
            "Giáo viên Test",
        )

        subject_id = repo.create_subject(
            connection,
            "TEST_TOAN",
            "Toán Test",
        )

        assessment = repo.create_assessment(
            connection,
            subject_id,
            school_year_id,
            "TEST_ASSESSMENT",
            1,
            "MIDTERM",
            date(2027, 10, 15),
        )

        assert class_id > 0
        assert subject_id > 0
        assert assessment.assessment_id > 0
        assert assessment.status == AssessmentStatus.ACTIVE

        assessment_id = assessment.assessment_id

    with test_db.transaction() as connection:
        school_year = repo.get_school_year_by_name(
            connection,
            "TEST_2027_2028",
        )

        assert school_year is not None
        assert school_year[0] == school_year_id

        subject = repo.get_subject_by_code(
            connection,
            "TEST_TOAN",
        )

        assert subject is not None
        assert subject[0] == subject_id

        classes = repo.list_classes_by_school_year(
            connection,
            school_year_id,
        )

        assert any(
            item[0] == class_id
            for item in classes
        )

        found_assessment = repo.get_assessment_by_id(
            connection,
            assessment_id,
        )

        assert found_assessment is not None
        assert found_assessment.assessment_name == "TEST_ASSESSMENT"

    cleanup(test_db)