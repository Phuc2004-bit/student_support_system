from datetime import date

from config.database import db_settings
from database.connection import DatabaseManager
from models.enums import AssessmentStatus
from repositories import AcademicRepository
from services import AcademicService


YEAR_1 = "A10_2627"
YEAR_2 = "A10_2728"
SUBJECT_1 = "A10_M1"
SUBJECT_2 = "A10_M2"
ASSESSMENTS = ("A10_A1", "A10_A2", "A10_A3", "A10_A4")


def get_test_db() -> DatabaseManager:
    connection_string = db_settings.connection_string().replace(
        "DATABASE=student_support_db;",
        "DATABASE=student_support_db_test;",
    )
    return DatabaseManager(connection_string)


def cleanup(db: DatabaseManager) -> None:
    with db.transaction() as connection:
        cursor = connection.cursor()
        cursor.execute(
            "DELETE FROM dbo.ASSESSMENTS WHERE assessment_name IN (?, ?, ?, ?)",
            *ASSESSMENTS,
        )
        cursor.execute(
            "DELETE FROM dbo.SUBJECTS WHERE subject_code IN (?, ?)",
            SUBJECT_1,
            SUBJECT_2,
        )
        cursor.execute(
            "DELETE FROM dbo.SCHOOL_YEARS WHERE year_name IN (?, ?)",
            YEAR_1,
            YEAR_2,
        )


def test_assessment_read_api_lists_by_year_and_subject():
    db = get_test_db()
    repository = AcademicRepository()
    service = AcademicService(db)

    cleanup(db)
    try:
        with db.transaction() as connection:
            year_1_id = repository.create_school_year(
                connection,
                YEAR_1,
                date(2026, 9, 1),
                date(2027, 5, 31),
            )
            year_2_id = repository.create_school_year(
                connection,
                YEAR_2,
                date(2027, 9, 1),
                date(2028, 5, 31),
            )
            subject_1_id = repository.create_subject(
                connection,
                SUBJECT_1,
                "Môn Một",
            )
            subject_2_id = repository.create_subject(
                connection,
                SUBJECT_2,
                "Môn Hai",
            )
            first = repository.create_assessment(
                connection,
                subject_1_id,
                year_1_id,
                ASSESSMENTS[0],
                1,
                "QUIZ",
                date(2026, 10, 1),
            )
            repository.create_assessment(
                connection,
                subject_1_id,
                year_1_id,
                ASSESSMENTS[1],
                2,
                "FINAL",
                date(2027, 5, 1),
            )
            repository.create_assessment(
                connection,
                subject_2_id,
                year_1_id,
                ASSESSMENTS[2],
                1,
                None,
                None,
            )
            repository.create_assessment(
                connection,
                subject_1_id,
                year_2_id,
                ASSESSMENTS[3],
                1,
                "QUIZ",
                date(2027, 10, 1),
            )

        found = service.get_assessment(first.assessment_id)
        year_items = service.list_assessments(year_1_id)
        subject_items = service.list_assessments(
            year_1_id,
            subject_id=subject_1_id,
        )
        semester_items = service.list_assessments(
            year_1_id,
            subject_id=subject_1_id,
            semester=2,
            status=AssessmentStatus.ACTIVE,
        )

        assert found == first
        assert {item.assessment_name for item in year_items} == set(
            ASSESSMENTS[:3]
        )
        assert [item.assessment_name for item in subject_items] == [
            ASSESSMENTS[0],
            ASSESSMENTS[1],
        ]
        assert [item.assessment_name for item in semester_items] == [
            ASSESSMENTS[1]
        ]
        assert all(
            isinstance(item.status, AssessmentStatus)
            for item in year_items
        )
    finally:
        cleanup(db)
