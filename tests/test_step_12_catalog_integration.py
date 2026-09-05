from datetime import date

import pytest

from config.database import db_settings
from database.connection import DatabaseManager
from exceptions import BusinessRuleError, DuplicateError
from models.dto import StudentCreateData
from repositories import EnrollmentRepository, StudentRepository
from services import AcademicService


YEAR_A = "T125_2035_2036"
YEAR_B = "T125_2036_2037"
CLASS_NAME = "T125_11A"
CLASS_RENAMED = "T125_11B"
GRADE_NUMBER = 11
GRADE_NAME = "T125 Grade 11"
GRADE_RENAMED = "T125 Grade Eleven"
STUDENT_ID = "T125-STUDENT-001"
STUDENT_CODE = "T125S01"


def get_test_db() -> DatabaseManager:
    connection_string = db_settings.connection_string().replace(
        "DATABASE=student_support_db;",
        "DATABASE=student_support_db_test;",
    )
    assert "DATABASE=student_support_db_test;" in connection_string
    return DatabaseManager(connection_string)


def cleanup(db: DatabaseManager) -> None:
    with db.transaction() as connection:
        cursor = connection.cursor()
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
            """
            DELETE c
            FROM dbo.CLASSES AS c
            INNER JOIN dbo.SCHOOL_YEARS AS sy
                ON sy.school_year_id = c.school_year_id
            WHERE sy.year_name IN (?, ?)
            """,
            YEAR_A,
            YEAR_B,
        )
        cursor.execute(
            "DELETE FROM dbo.SCHOOL_YEARS WHERE year_name IN (?, ?)",
            YEAR_A,
            YEAR_B,
        )
        cursor.execute(
            """
            DELETE FROM dbo.GRADES
            WHERE grade_number = ?
              AND grade_name IN (?, ?)
            """,
            GRADE_NUMBER,
            GRADE_NAME,
            GRADE_RENAMED,
        )


def test_catalog_crud_filters_and_history_safety_against_test_database():
    db = get_test_db()
    service = AcademicService(db)
    student_repository = StudentRepository()
    enrollment_repository = EnrollmentRepository()

    cleanup(db)
    try:
        grade_id = service.create_grade(GRADE_NUMBER, GRADE_NAME)
        service.update_grade_name(grade_id, GRADE_RENAMED)

        grades = service.list_catalog_grades()
        grade = next(item for item in grades if item.grade_id == grade_id)
        assert grade.grade_number == GRADE_NUMBER
        assert grade.grade_name == GRADE_RENAMED

        year_a_id = service.create_school_year(
            YEAR_A,
            date(2035, 9, 1),
            date(2036, 5, 31),
            False,
        )
        year_b_id = service.create_school_year(
            YEAR_B,
            date(2036, 9, 1),
            date(2037, 5, 31),
            False,
        )
        service.update_school_year(
            year_a_id,
            YEAR_A,
            date(2035, 8, 25),
            date(2036, 5, 25),
            False,
        )

        years = service.list_catalog_school_years()
        year_a = next(item for item in years if item.school_year_id == year_a_id)
        assert year_a.start_date == date(2035, 8, 25)
        assert year_a.end_date == date(2036, 5, 25)
        assert year_a.is_current is False

        with pytest.raises(DuplicateError):
            service.create_school_year(
                YEAR_A,
                date(2035, 9, 1),
                date(2036, 5, 31),
                False,
            )

        class_id = service.create_class(
            CLASS_NAME,
            grade_id,
            year_a_id,
            "Teacher 125",
        )
        with pytest.raises(DuplicateError):
            service.create_class(CLASS_NAME, grade_id, year_a_id)

        classes = service.list_catalog_classes(year_a_id, grade_id)
        assert [item.class_id for item in classes] == [class_id]
        assert classes[0].school_year_id == year_a_id
        assert classes[0].grade_id == grade_id
        assert classes[0].is_active is True
        assert service.list_catalog_classes(year_b_id, grade_id) == []

        with db.transaction() as connection:
            student_repository.create(
                connection,
                STUDENT_ID,
                StudentCreateData(STUDENT_CODE, "Student 125"),
            )
            enrollment = enrollment_repository.create(
                connection,
                STUDENT_ID,
                class_id,
                date(2035, 9, 1),
            )

        service.update_class(
            class_id,
            CLASS_RENAMED,
            grade_id,
            year_a_id,
            "Teacher Updated",
            "ACTIVE",
        )
        with pytest.raises(BusinessRuleError):
            service.update_class(
                class_id,
                CLASS_RENAMED,
                grade_id,
                year_b_id,
                "Teacher Updated",
                "ACTIVE",
            )

        service.set_class_active(class_id, False)
        stored = service.list_catalog_classes(year_a_id, grade_id)[0]
        assert stored.class_name == CLASS_RENAMED
        assert stored.homeroom_teacher == "Teacher Updated"
        assert stored.status == "INACTIVE"
        assert stored.is_active is False

        selector_row = next(
            item
            for item in service.list_classes_by_school_year(year_a_id)
            if item[0] == class_id
        )
        assert selector_row[-1] is False

        with db.transaction() as connection:
            preserved = enrollment_repository.get_by_id(
                connection,
                enrollment.enrollment_id,
            )
        assert preserved is not None
        assert preserved.class_id == class_id
    finally:
        cleanup(db)
