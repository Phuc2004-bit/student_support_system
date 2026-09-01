from datetime import date
from decimal import Decimal

import pytest
from openpyxl import Workbook

from config.database import db_settings
from database.connection import DatabaseManager
from exceptions import DuplicateError, ValidationError
from models.dto import StudentCreateData
from models.dto.import_dto import (
    ScoreImportPreview,
    ScoreImportPreviewRow,
)
from models.enums import InterventionStatus
from repositories import (
    AcademicRepository,
    EnrollmentRepository,
    InterventionRepository,
    ScoreRepository,
    StudentRepository,
    SupportRuleRepository,
)
from services.import_service import ImportService


TEST_YEAR = "THARD_2026_2027"
TEST_CLASS = "THARD_10A1"
TEST_SUBJECT = "THARD_TOAN"
TEST_ASSESSMENT_1 = "THARD_ASSESSMENT_1"
TEST_ASSESSMENT_2 = "THARD_ASSESSMENT_2"
TEST_CODES = (
    "THARD_HS001",
    "THARD_HS002",
    "THARD_HS003",
    "THARD_HS004",
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
                WHERE s.student_code IN (?, ?, ?, ?)
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
                WHERE s.student_code IN (?, ?, ?, ?)
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
                WHERE s.student_code IN (?, ?, ?, ?)
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
            WHERE assessment_name IN (?, ?)
            """,
            TEST_ASSESSMENT_1,
            TEST_ASSESSMENT_2,
        )

        cursor.execute(
            """
            DELETE FROM dbo.STUDENT_ENROLLMENTS
            WHERE student_id IN
            (
                SELECT student_id
                FROM dbo.STUDENTS
                WHERE student_code IN (?, ?, ?, ?)
            )
            """,
            *TEST_CODES,
        )

        cursor.execute(
            """
            DELETE FROM dbo.STUDENTS
            WHERE student_code IN (?, ?, ?, ?)
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
            "Toán Hardening Test",
        )

        assessment_1 = academic_repo.create_assessment(
            connection,
            subject_id,
            school_year_id,
            TEST_ASSESSMENT_1,
            1,
            "MIDTERM",
            date(2026, 10, 15),
        )

        assessment_2 = academic_repo.create_assessment(
            connection,
            subject_id,
            school_year_id,
            TEST_ASSESSMENT_2,
            1,
            "REVIEW",
            date(2026, 11, 15),
        )

        rule_repo.create(
            connection,
            subject_id,
            school_year_id,
            Decimal("3.50"),
        )

        enrollment_ids = []

        for index, code in enumerate(TEST_CODES, start=1):
            student_id = f"thard-student-{index}"

            student_repo.create(
                connection,
                student_id,
                StudentCreateData(
                    student_code=code,
                    full_name=f"Học sinh Hardening {index}",
                ),
            )

            enrollment = enrollment_repo.create(
                connection,
                student_id,
                class_id,
                date(2026, 9, 7),
            )
            enrollment_ids.append(enrollment.enrollment_id)

    return {
        "subject_id": subject_id,
        "school_year_id": school_year_id,
        "assessment_1_id": assessment_1.assessment_id,
        "assessment_2_id": assessment_2.assessment_id,
        "enrollment_ids": tuple(enrollment_ids),
    }


def create_xlsx(path, rows, headers=None):
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Diem"

    worksheet.append(
        headers or ["Mã học sinh", "Điểm"]
    )

    for row in rows:
        worksheet.append(row)

    workbook.save(path)
    workbook.close()


def count_scores(test_db, assessment_id):
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


def test_invalid_preview_cannot_be_confirmed():
    test_db = get_test_db()
    service = ImportService(test_db)

    preview = ScoreImportPreview(
        file_name="invalid.xlsx",
        assessment_id=1,
        rows=(
            ScoreImportPreviewRow(
                row_number=2,
                student_code="HS_INVALID",
                full_name=None,
                class_name=None,
                score=None,
                enrollment_id=None,
                errors=("Điểm không hợp lệ.",),
            ),
        ),
    )

    assert preview.can_confirm is False

    with pytest.raises(ValidationError):
        service.confirm_score_import(preview)


def test_database_change_after_preview_is_detected(
    tmp_path,
):
    test_db = get_test_db()
    cleanup(test_db)

    try:
        seeded = seed_data(test_db)

        file_path = tmp_path / "db_changed.xlsx"
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
            seeded["assessment_1_id"],
        )

        assert preview.can_confirm is True

        # Sau Preview, DB thay đổi:
        # người khác nhập điểm cho HS002 trước khi Confirm.
        score_repo = ScoreRepository()

        with test_db.transaction() as connection:
            score_repo.create(
                connection,
                seeded["enrollment_ids"][1],
                seeded["assessment_1_id"],
                Decimal("6.00"),
            )

        with pytest.raises(DuplicateError):
            service.confirm_score_import(preview)

        # Không được commit HS001.
        # Chỉ còn score được tạo bên ngoài sau Preview.
        assert (
            count_scores(
                test_db,
                seeded["assessment_1_id"],
            )
            == 1
        )
    finally:
        cleanup(test_db)


def test_score_boundaries_zero_threshold_and_ten(
    tmp_path,
):
    test_db = get_test_db()
    cleanup(test_db)

    try:
        seeded = seed_data(test_db)

        file_path = tmp_path / "boundaries.xlsx"
        create_xlsx(
            file_path,
            [
                [TEST_CODES[0], 0.00],
                [TEST_CODES[1], 3.49],
                [TEST_CODES[2], 3.50],
                [TEST_CODES[3], 10.00],
            ],
        )

        service = ImportService(test_db)
        preview = service.preview_score_import(
            file_path,
            seeded["assessment_1_id"],
        )

        assert preview.can_confirm is True

        result = service.confirm_score_import(
            preview
        )

        assert result.imported_count == 4

        # 0.00 và 3.49 dưới 3.50 => 2 hồ sơ DETECTED.
        assert (
            result.detected_intervention_count
            == 2
        )

        with test_db.transaction() as connection:
            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM dbo.INTERVENTIONS
                WHERE subject_id = ?
                  AND status = ?
                """,
                seeded["subject_id"],
                InterventionStatus.DETECTED.value,
            )

            assert cursor.fetchone()[0] == 2
    finally:
        cleanup(test_db)


def test_existing_open_intervention_is_not_duplicated(
    tmp_path,
):
    test_db = get_test_db()
    cleanup(test_db)

    try:
        seeded = seed_data(test_db)

        score_repo = ScoreRepository()
        intervention_repo = InterventionRepository()

        # Tạo hồ sơ DETECTED từ assessment 1 trước.
        with test_db.transaction() as connection:
            trigger_score = score_repo.create(
                connection,
                seeded["enrollment_ids"][0],
                seeded["assessment_1_id"],
                Decimal("2.00"),
            )

            intervention = intervention_repo.create(
                connection,
                seeded["enrollment_ids"][0],
                seeded["subject_id"],
                trigger_score.score_id,
                date(2026, 10, 15),
            )

        file_path = tmp_path / "open_case.xlsx"
        create_xlsx(
            file_path,
            [
                [TEST_CODES[0], 2.50],
            ],
        )

        service = ImportService(test_db)
        preview = service.preview_score_import(
            file_path,
            seeded["assessment_2_id"],
        )

        result = service.confirm_score_import(
            preview
        )

        assert result.imported_count == 1

        # _detect_from_score trả lại existing open case,
        # nhưng không được tạo case thứ hai.
        with test_db.transaction() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM dbo.INTERVENTIONS
                WHERE enrollment_id = ?
                  AND subject_id = ?
                """,
                seeded["enrollment_ids"][0],
                seeded["subject_id"],
            )
            assert cursor.fetchone()[0] == 1

            cursor.execute(
                """
                SELECT intervention_id
                FROM dbo.INTERVENTIONS
                WHERE enrollment_id = ?
                  AND subject_id = ?
                """,
                seeded["enrollment_ids"][0],
                seeded["subject_id"],
            )
            assert cursor.fetchone()[0] == intervention.intervention_id
    finally:
        cleanup(test_db)


def test_empty_file_and_missing_required_header_are_blocked(
    tmp_path,
):
    test_db = get_test_db()
    service = ImportService(test_db)

    empty_path = tmp_path / "empty.xlsx"
    create_xlsx(
        empty_path,
        [],
    )

    with pytest.raises(ValidationError):
        service.preview_score_import(
            empty_path,
            assessment_id=1,
        )

    missing_header_path = (
        tmp_path / "missing_header.xlsx"
    )
    create_xlsx(
        missing_header_path,
        [["HS001"]],
        headers=["Mã học sinh"],
    )

    with pytest.raises(ValidationError):
        service.preview_score_import(
            missing_header_path,
            assessment_id=1,
        )
