from datetime import date

from config.database import db_settings
from database.connection import DatabaseManager
from exceptions import DuplicateError
from repositories import AcademicRepository
from services import AcademicService


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
            WHERE assessment_name = N'TEST_SVC_ASSESSMENT'
            """
        )

        cursor.execute(
            """
            DELETE FROM dbo.CLASSES
            WHERE class_name = N'TEST_SVC_ACADEMIC_10A1'
            """
        )

        cursor.execute(
            """
            DELETE FROM dbo.SUBJECTS
            WHERE subject_code = 'TEST_SVC_TOAN'
            """
        )

        cursor.execute(
            """
            DELETE FROM dbo.SCHOOL_YEARS
            WHERE year_name = 'TEST_SVC_2028_2029'
            """
        )


def test_academic_service_flow():
    test_db = get_test_db()

    service = AcademicService(test_db)
    repo = AcademicRepository()

    cleanup(test_db)

    try:
        # =============================================
        # SEED GRADE
        # =============================================
        with test_db.transaction() as connection:
            cursor = connection.cursor()

            # grade_number là UNIQUE; GRADES là dữ liệu nền dùng chung.
            # Tái sử dụng Khối 10 nếu đã tồn tại.
            cursor.execute(
                """
                SELECT grade_id
                FROM dbo.GRADES
                WHERE grade_number = ?
                """,
                10,
            )
            grade_row = cursor.fetchone()

            if grade_row is not None:
                grade_id = grade_row[0]
            else:
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
                    "Khối 10",
                )
                grade_id = cursor.fetchone()[0]

        # =============================================
        # SCHOOL YEAR
        # =============================================
        school_year_id = service.create_school_year(
            "TEST_SVC_2028_2029",
            date(2028, 9, 1),
            date(2029, 5, 31),
            False,
        )

        assert school_year_id > 0

        school_year = service.get_school_year(
            "TEST_SVC_2028_2029"
        )

        assert school_year[0] == school_year_id

        duplicate_year_blocked = False

        try:
            service.create_school_year(
                "TEST_SVC_2028_2029",
                date(2028, 9, 1),
                date(2029, 5, 31),
                False,
            )
        except DuplicateError:
            duplicate_year_blocked = True

        assert duplicate_year_blocked is True

        # =============================================
        # CLASS
        # =============================================
        class_id = service.create_class(
            "TEST_SVC_ACADEMIC_10A1",
            grade_id,
            school_year_id,
            "Giáo viên Test",
        )

        assert class_id > 0

        class_info = service.get_class(class_id)

        assert class_info[0] == class_id
        assert class_info[1] == "TEST_SVC_ACADEMIC_10A1"

        classes = service.list_classes_by_school_year(
            school_year_id
        )

        assert any(
            item[0] == class_id
            for item in classes
        )

        # =============================================
        # SUBJECT
        # =============================================
        subject_id = service.create_subject(
            "test_svc_toan",
            "Toán Service Test",
        )

        assert subject_id > 0

        subject = service.get_subject(
            "test_svc_toan"
        )

        assert subject[0] == subject_id
        assert subject[1] == "TEST_SVC_TOAN"

        duplicate_subject_blocked = False

        try:
            service.create_subject(
                "TEST_SVC_TOAN",
                "Toán Duplicate",
            )
        except DuplicateError:
            duplicate_subject_blocked = True

        assert duplicate_subject_blocked is True

        # =============================================
        # ASSESSMENT
        # =============================================
        assessment = service.create_assessment(
            subject_id,
            school_year_id,
            "TEST_SVC_ASSESSMENT",
            1,
            "MIDTERM",
            date(2028, 10, 15),
        )

        assert assessment.assessment_id > 0
        assert (
            assessment.assessment_name
            == "TEST_SVC_ASSESSMENT"
        )

        found = service.get_assessment(
            assessment.assessment_id
        )

        assert (
            found.assessment_id
            == assessment.assessment_id
        )

    finally:
        cleanup(test_db)