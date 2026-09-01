from decimal import Decimal

from models.dto.import_dto import (
    ScoreImportCommitResult,
    ScoreImportPreview,
    ScoreImportPreviewRow,
    ScoreImportRawRow,
)


def test_score_import_raw_row():
    row = ScoreImportRawRow(
        row_number=2,
        student_code=" HS001 ",
        full_name="Nguyễn Văn A",
        class_name="10A1",
        score="2.8",
    )

    assert row.row_number == 2
    assert row.student_code == " HS001 "
    assert row.score == "2.8"


def test_score_import_preview_all_valid():
    rows = (
        ScoreImportPreviewRow(
            row_number=2,
            student_code="HS001",
            full_name="Nguyễn Văn A",
            class_name="10A1",
            score=Decimal("2.80"),
            enrollment_id=1001,
        ),
        ScoreImportPreviewRow(
            row_number=3,
            student_code="HS002",
            full_name="Trần Văn B",
            class_name="10A1",
            score=Decimal("4.00"),
            enrollment_id=1002,
        ),
    )

    preview = ScoreImportPreview(
        file_name="diem_toan.xlsx",
        assessment_id=10,
        rows=rows,
    )

    assert preview.total_rows == 2
    assert preview.valid_rows == 2
    assert preview.invalid_rows == 0
    assert preview.can_confirm is True


def test_score_import_preview_has_invalid_row():
    rows = (
        ScoreImportPreviewRow(
            row_number=2,
            student_code="HS001",
            full_name="Nguyễn Văn A",
            class_name="10A1",
            score=Decimal("2.80"),
            enrollment_id=1001,
        ),
        ScoreImportPreviewRow(
            row_number=3,
            student_code="HS002",
            full_name="Trần Văn B",
            class_name="10A1",
            score=None,
            enrollment_id=1002,
            errors=("Điểm không hợp lệ.",),
        ),
    )

    preview = ScoreImportPreview(
        file_name="diem_toan.xlsx",
        assessment_id=10,
        rows=rows,
    )

    assert preview.total_rows == 2
    assert preview.valid_rows == 1
    assert preview.invalid_rows == 1
    assert preview.can_confirm is False


def test_score_import_commit_result():
    result = ScoreImportCommitResult(
        assessment_id=10,
        imported_count=35,
        detected_intervention_count=7,
    )

    assert result.imported_count == 35
    assert result.detected_intervention_count == 7
