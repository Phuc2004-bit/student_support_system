from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
from openpyxl import Workbook

from exceptions import ValidationError
from services.import_service import ImportService


class FakeDatabaseManager:
    @contextmanager
    def transaction(self):
        yield object()


class FakeStudentRepository:
    def __init__(self):
        self.students = {
            "HS001": SimpleNamespace(
                student_id="student-1",
                student_code="HS001",
                full_name="Nguyễn Văn A",
            ),
            "HS002": SimpleNamespace(
                student_id="student-2",
                student_code="HS002",
                full_name="Trần Thị B",
            ),
        }

    def get_by_code(
        self,
        connection,
        student_code,
    ):
        return self.students.get(student_code)


class FakeEnrollmentRepository:
    def __init__(self):
        self.active = {
            "student-1": SimpleNamespace(
                enrollment_id=101,
            ),
            "student-2": SimpleNamespace(
                enrollment_id=102,
            ),
        }

    def get_active_by_student(
        self,
        connection,
        student_id,
    ):
        return self.active.get(student_id)

    def list_by_student(
        self,
        connection,
        student_id,
    ):
        enrollment = self.active.get(student_id)

        if enrollment is None:
            return []

        return [
            SimpleNamespace(
                enrollment_id=enrollment.enrollment_id,
                class_name="10A1",
            )
        ]


class FakeAcademicRepository:
    def get_assessment_by_id(
        self,
        connection,
        assessment_id,
    ):
        if assessment_id == 10:
            return SimpleNamespace(
                assessment_id=10,
            )

        return None


def build_service():
    return ImportService(
        db=FakeDatabaseManager(),
        student_repository=FakeStudentRepository(),
        enrollment_repository=FakeEnrollmentRepository(),
        academic_repository=FakeAcademicRepository(),
    )


def create_xlsx(
    path: Path,
    rows: list[list],
):
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Diem"

    worksheet.append(
        [
            "Mã học sinh",
            "Họ tên",
            "Lớp",
            "Điểm",
        ]
    )

    for row in rows:
        worksheet.append(row)

    workbook.save(path)
    workbook.close()


def test_preview_valid_file(tmp_path):
    path = tmp_path / "valid.xlsx"

    create_xlsx(
        path,
        [
            [
                " hs001 ",
                "Nguyễn Văn A",
                "10A1",
                "2,8",
            ],
            [
                "HS002",
                "Trần Thị B",
                "10A1",
                4,
            ],
        ],
    )

    preview = build_service().preview_score_import(
        path,
        assessment_id=10,
    )

    assert preview.total_rows == 2
    assert preview.valid_rows == 2
    assert preview.invalid_rows == 0
    assert preview.can_confirm is True

    assert (
        preview.rows[0].student_code
        == "HS001"
    )
    assert (
        preview.rows[0].score
        == Decimal("2.80")
    )
    assert (
        preview.rows[0].enrollment_id
        == 101
    )


def test_preview_collects_row_errors(tmp_path):
    path = tmp_path / "invalid.xlsx"

    create_xlsx(
        path,
        [
            [
                "UNKNOWN",
                "Không tồn tại",
                "10A1",
                2.5,
            ],
            [
                "HS001",
                "Nguyễn Văn A",
                "10A2",
                11,
            ],
            [
                "HS001",
                "Nguyễn Văn A",
                "10A1",
                3.0,
            ],
        ],
    )

    preview = build_service().preview_score_import(
        path,
        assessment_id=10,
    )

    assert preview.total_rows == 3
    assert preview.invalid_rows == 3
    assert preview.can_confirm is False

    assert any(
        "Không tìm thấy học sinh"
        in error
        for error in preview.rows[0].errors
    )

    assert any(
        "0 đến 10"
        in error
        for error in preview.rows[1].errors
    )

    assert any(
        "không khớp lớp hiện tại"
        in error
        for error in preview.rows[1].errors
    )

    assert any(
        "bị lặp"
        in error
        for error in preview.rows[2].errors
    )


def test_preview_name_mismatch_is_warning(tmp_path):
    path = tmp_path / "warning.xlsx"

    create_xlsx(
        path,
        [
            [
                "HS001",
                "Tên khác",
                "10A1",
                3.5,
            ],
        ],
    )

    preview = build_service().preview_score_import(
        path,
        assessment_id=10,
    )

    assert preview.valid_rows == 1
    assert preview.can_confirm is True
    assert len(preview.rows[0].warnings) == 1


def test_missing_required_header_is_blocked(
    tmp_path,
):
    path = tmp_path / "missing_header.xlsx"

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.append(
        [
            "Mã học sinh",
            "Họ tên",
            "Lớp",
        ]
    )
    worksheet.append(
        [
            "HS001",
            "Nguyễn Văn A",
            "10A1",
        ]
    )
    workbook.save(path)
    workbook.close()

    with pytest.raises(ValidationError):
        build_service().preview_score_import(
            path,
            assessment_id=10,
        )


def test_unknown_assessment_is_blocked(
    tmp_path,
):
    path = tmp_path / "assessment.xlsx"

    create_xlsx(
        path,
        [
            [
                "HS001",
                "Nguyễn Văn A",
                "10A1",
                2.8,
            ],
        ],
    )

    with pytest.raises(ValidationError):
        build_service().preview_score_import(
            path,
            assessment_id=999,
        )
