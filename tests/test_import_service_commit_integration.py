from datetime import date
from decimal import Decimal

import pytest
from openpyxl import Workbook

from config.database import db_settings
from database.connection import DatabaseManager
from exceptions import DuplicateError, MissingSupportRuleError
from models.dto import StudentCreateData
from repositories import (
    AcademicRepository,
    EnrollmentRepository,
    InterventionRepository,
    ScoreRepository,
    StudentRepository,
    SupportRuleRepository,
)
from services.import_service import ImportService


TEST_YEAR = "TIMP_2026_2027"
TEST_CLASS = "TIMP_10A1"
TEST_SUBJECT = "TIMP_TOAN"
TEST_ASSESSMENT = "TIMP_ASSESSMENT"
TEST_CODES = (
    "TIMP_HS001",
    "TIMP_HS002",
    "TIMP_HS003",
)


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
                WHERE s.student_code IN (?, ?, ?)
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
                WHERE s.student_code IN (?, ?, ?)
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
                WHERE s.student_code IN (?, ?, ?)
            )
            """,
            *TEST_CODES,
        )

        cursor.execute(
            """
            DELETE FROM dbo.SUPPORT_RULES
            WHERE subject_id IN
            (
                SELECT subject_id
                FROM dbo.SUBJECTS
                WHERE subject_code = ?
            )
            """,
            TEST_SUBJECT,
        )

        cursor.execute(
            """
            DELETE FROM dbo.ASSESSMENTS
            WHERE assessment_name = ?
            """,
            TEST_ASSESSMENT,
        )

        cursor.execute(
            """
            DELETE FROM dbo.STUDENT_ENROLLMENTS
            WHERE student_id IN
            (
                SELECT student_id
                FROM dbo.STUDENTS
                WHERE student_code IN (?, ?, ?)
            )
            """,
            *TEST_CODES,
        )

        cursor.execute(
            """
            DELETE FROM dbo.STUDENTS
            WHERE student_code IN (?, ?, ?)
            """,
            *TEST_CODES,
        )

        cursor.execute(
            """
            DELETE FROM dbo.CLASSES
            WHERE class_name = ?
            """,
            TEST_CLASS,
        )

        cursor.execute(
            """
            DELETE FROM dbo.SUBJECTS
            WHERE subject_code = ?
            """,
            TEST_SUBJECT,
        )

        cursor.execute(
            """
            DELETE FROM dbo.SCHOOL_YEARS
            WHERE year_name = ?
            """,
            TEST_YEAR,
        )


def seed_data(test_db: DatabaseManager):
    academic_repo = AcademicRepository()
    student_repo = StudentRepository()
    enrollment_repo = EnrollmentRepository()
    rule_repo = SupportRuleRepository()

    with test_db.transaction() as connection:
        cursor = connection.cursor()

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

        school_year_id = (
            academic_repo.create_school_year(
                connection,
                TEST_YEAR,
                date(2026, 9, 7),
                date(2027, 5, 31),
                False,
            )
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
            "Toán Import Test",
        )

        assessment = (
            academic_repo.create_assessment(
                connection,
                subject_id,
                school_year_id,
                TEST_ASSESSMENT,
                1,
                "MIDTERM",
                date(2026, 10, 15),
            )
        )

        rule_repo.create(
            connection,
            subject_id,
            school_year_id,
            Decimal("3.50"),
        )

        enrollment_ids = []

        for index, code in enumerate(
            TEST_CODES,
            start=1,
        ):
            student_id = f"timp-student-{index}"

            student_repo.create(
                connection,
                student_id,
                StudentCreateData(
                    student_code=code,
                    full_name=f"Học sinh Import {index}",
                ),
            )

            enrollment = enrollment_repo.create(
                connection,
                student_id,
                class_id,
                date(2026, 9, 7),
            )
            enrollment_ids.append(
                enrollment.enrollment_id
            )

    return {
        "assessment_id": assessment.assessment_id,
        "subject_id": subject_id,
        "school_year_id": school_year_id,
        "enrollment_ids": tuple(enrollment_ids),
    }


def create_xlsx(path, rows):
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Diem"

    # Chỉ dùng 2 cột bắt buộc để test commit,
    # tránh phụ thuộc UI/lớp khi test transaction.
    worksheet.append(
        ["Mã học sinh", "Điểm"]
    )

    for row in rows:
        worksheet.append(row)

    workbook.save(path)
    workbook.close()


def count_scores(
    test_db,
    assessment_id,
):
    with test_db.transaction() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM dbo.SCORES
            WHERE assessment_id = ?
            """,
            assessment_id,
        )
        return cursor.fetchone()[0]


def count_interventions(
    test_db,
    subject_id,
):
    with test_db.transaction() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM dbo.INTERVENTIONS
            WHERE subject_id = ?
              AND enrollment_id IN
              (
                  SELECT e.enrollment_id
                  FROM dbo.STUDENT_ENROLLMENTS e
                  JOIN dbo.STUDENTS s
                    ON s.student_id = e.student_id
                  WHERE s.student_code IN (?, ?, ?)
              )
            """,
            subject_id,
            *TEST_CODES,
        )
        return cursor.fetchone()[0]


def test_import_commit_is_atomic_and_detects_support(
    tmp_path,
):
    test_db = get_test_db()
    cleanup(test_db)

    try:
        seeded = seed_data(test_db)

        file_path = tmp_path / "valid_import.xlsx"
        create_xlsx(
            file_path,
            [
                [TEST_CODES[0], 2.80],
                [TEST_CODES[1], 3.50],
                [TEST_CODES[2], 7.00],
            ],
        )

        service = ImportService(test_db)

        preview = service.preview_score_import(
            file_path,
            seeded["assessment_id"],
        )

        assert preview.can_confirm is True

        result = service.confirm_score_import(
            preview
        )

        assert result.imported_count == 3
        assert (
            result.detected_intervention_count
            == 1
        )

        assert (
            count_scores(
                test_db,
                seeded["assessment_id"],
            )
            == 3
        )

        assert (
            count_interventions(
                test_db,
                seeded["subject_id"],
            )
            == 1
        )
    finally:
        cleanup(test_db)


def test_duplicate_existing_score_rolls_back_batch(
    tmp_path,
):
    test_db = get_test_db()
    cleanup(test_db)

    try:
        seeded = seed_data(test_db)
        score_repo = ScoreRepository()

        with test_db.transaction() as connection:
            score_repo.create(
                connection,
                seeded["enrollment_ids"][1],
                seeded["assessment_id"],
                Decimal("6.00"),
            )

        file_path = tmp_path / "duplicate.xlsx"
        create_xlsx(
            file_path,
            [
                [TEST_CODES[0], 5.00],
                [TEST_CODES[1], 6.00],
            ],
        )

        service = ImportService(test_db)
        preview = service.preview_score_import(
            file_path,
            seeded["assessment_id"],
        )

        with pytest.raises(DuplicateError):
            service.confirm_score_import(
                preview
            )

        # Chỉ còn score seed từ trước.
        # Dòng HS001 không được commit.
        assert (
            count_scores(
                test_db,
                seeded["assessment_id"],
            )
            == 1
        )
    finally:
        cleanup(test_db)


def test_missing_support_rule_rolls_back_all_scores(
    tmp_path,
):
    test_db = get_test_db()
    cleanup(test_db)

    try:
        seeded = seed_data(test_db)

        with test_db.transaction() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                DELETE FROM dbo.SUPPORT_RULES
                WHERE subject_id = ?
                  AND school_year_id = ?
                """,
                seeded["subject_id"],
                seeded["school_year_id"],
            )

        file_path = tmp_path / "missing_rule.xlsx"
        create_xlsx(
            file_path,
            [
                [TEST_CODES[0], 8.00],
                [TEST_CODES[1], 2.50],
            ],
        )

        service = ImportService(test_db)
        preview = service.preview_score_import(
            file_path,
            seeded["assessment_id"],
        )

        with pytest.raises(
            MissingSupportRuleError
        ):
            service.confirm_score_import(
                preview
            )

        # Dòng 8.00 được insert trước trong transaction,
        # nhưng lỗi support rule ở quá trình detect
        # phải rollback cả batch.
        assert (
            count_scores(
                test_db,
                seeded["assessment_id"],
            )
            == 0
        )
    finally:
        cleanup(test_db)
