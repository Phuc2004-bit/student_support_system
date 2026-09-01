from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

from database.connection import DatabaseManager
from exceptions import DuplicateError, ValidationError
from models.dto.import_dto import (
    ScoreImportCommitResult,
    ScoreImportPreview,
    ScoreImportPreviewRow,
)
from repositories import (
    AcademicRepository,
    EnrollmentRepository,
    InterventionRepository,
    ScoreRepository,
    StudentRepository,
    SupportRuleRepository,
)
from services.support_service import SupportService


class ImportService:
    """
    Bước 5.8B.1:
    READ -> NORMALIZE -> VALIDATE -> RESOLVE -> PREVIEW

    Lưu ý:
    - preview_score_import() KHÔNG ghi SCORES.
    - preview_score_import() KHÔNG tạo INTERVENTIONS.
    - Confirm/transaction ghi dữ liệu sẽ được triển khai ở 5.8B.2.
    """

    REQUIRED_HEADERS = {
        "student_code",
        "score",
    }

    HEADER_ALIASES = {
        "ma hoc sinh": "student_code",
        "mã học sinh": "student_code",
        "ma hs": "student_code",
        "mã hs": "student_code",
        "student code": "student_code",
        "student_code": "student_code",

        "ho ten": "full_name",
        "họ tên": "full_name",
        "ho va ten": "full_name",
        "họ và tên": "full_name",
        "full name": "full_name",
        "full_name": "full_name",

        "lop": "class_name",
        "lớp": "class_name",
        "class": "class_name",
        "class name": "class_name",
        "class_name": "class_name",

        "diem": "score",
        "điểm": "score",
        "score": "score",
    }

    def __init__(
        self,
        db: DatabaseManager,
        student_repository: StudentRepository | None = None,
        enrollment_repository: EnrollmentRepository | None = None,
        academic_repository: AcademicRepository | None = None,
        score_repository: ScoreRepository | None = None,
        rule_repository: SupportRuleRepository | None = None,
        intervention_repository: InterventionRepository | None = None,
    ):
        self.db = db
        self.student_repository = (
            student_repository
            or StudentRepository()
        )
        self.enrollment_repository = (
            enrollment_repository
            or EnrollmentRepository()
        )
        self.academic_repository = (
            academic_repository
            or AcademicRepository()
        )
        self.score_repository = (
            score_repository
            or ScoreRepository()
        )
        self.rule_repository = (
            rule_repository
            or SupportRuleRepository()
        )
        self.intervention_repository = (
            intervention_repository
            or InterventionRepository()
        )

    def preview_score_import(
        self,
        file_path: str | Path,
        assessment_id: int,
    ) -> ScoreImportPreview:
        """
        Đọc file Excel và trả về Preview.

        Không INSERT/UPDATE database.
        """
        if assessment_id <= 0:
            raise ValidationError(
                "assessment_id không hợp lệ."
            )

        path = Path(file_path)

        if not path.exists() or not path.is_file():
            raise ValidationError(
                "Không tìm thấy file Excel."
            )

        if path.suffix.lower() != ".xlsx":
            raise ValidationError(
                "V1.0 chỉ hỗ trợ file .xlsx."
            )

        raw_rows = self._read_excel(path)

        if not raw_rows:
            raise ValidationError(
                "File Excel không có dữ liệu để import."
            )

        with self.db.transaction() as connection:
            assessment = (
                self.academic_repository.get_assessment_by_id(
                    connection,
                    assessment_id,
                )
            )

            if assessment is None:
                raise ValidationError(
                    "Không tìm thấy đợt đánh giá."
                )

            preview_rows = self._build_preview_rows(
                connection=connection,
                raw_rows=raw_rows,
            )

        return ScoreImportPreview(
            file_name=path.name,
            assessment_id=assessment_id,
            rows=tuple(preview_rows),
        )

    def confirm_score_import(
        self,
        preview: ScoreImportPreview,
    ) -> ScoreImportCommitResult:
        """
        CONFIRM -> ONE TRANSACTION -> INSERT SCORES
        -> DETECT SUPPORT -> COMMIT/ROLLBACK.

        V1.0: all-or-nothing.
        """
        if preview is None:
            raise ValidationError(
                "Preview import không được để trống."
            )

        if preview.assessment_id <= 0:
            raise ValidationError(
                "assessment_id không hợp lệ."
            )

        if not preview.can_confirm:
            raise ValidationError(
                "Không thể import vì Preview còn dòng lỗi."
            )

        if not preview.rows:
            raise ValidationError(
                "Không có dữ liệu để import."
            )

        with self.db.transaction() as connection:
            assessment = (
                self.academic_repository
                .get_assessment_by_id(
                    connection,
                    preview.assessment_id,
                )
            )

            if assessment is None:
                raise ValidationError(
                    "Không tìm thấy đợt đánh giá."
                )

            # Re-validate dữ liệu quan trọng ngay trong transaction.
            # Không tin tuyệt đối vào Preview cũ vì DB có thể đã thay đổi.
            seen_enrollment_ids: set[int] = set()

            for row in preview.rows:
                if row.enrollment_id is None:
                    raise ValidationError(
                        f"Dòng {row.row_number}: "
                        "không xác định được enrollment_id."
                    )

                if row.score is None:
                    raise ValidationError(
                        f"Dòng {row.row_number}: "
                        "điểm không hợp lệ."
                    )

                if row.enrollment_id in seen_enrollment_ids:
                    raise DuplicateError(
                        f"Dòng {row.row_number}: "
                        "học sinh bị lặp trong batch import."
                    )

                seen_enrollment_ids.add(
                    row.enrollment_id
                )

                existing = (
                    self.score_repository
                    .get_by_enrollment_assessment(
                        connection,
                        row.enrollment_id,
                        preview.assessment_id,
                    )
                )

                if existing is not None:
                    raise DuplicateError(
                        f"Dòng {row.row_number}: "
                        f"học sinh {row.student_code} "
                        "đã có điểm cho đợt đánh giá này."
                    )

            support_service = SupportService(
                db=self.db,
                score_repository=self.score_repository,
                academic_repository=self.academic_repository,
                rule_repository=self.rule_repository,
                intervention_repository=(
                    self.intervention_repository
                ),
            )

            imported_count = 0
            detected_ids: set[int] = set()

            for row in preview.rows:
                score = self.score_repository.create(
                    connection,
                    row.enrollment_id,
                    preview.assessment_id,
                    row.score,
                )

                intervention = (
                    support_service._detect_from_score(
                        connection,
                        score.score_id,
                    )
                )

                imported_count += 1

                if intervention is not None:
                    detected_ids.add(
                        intervention.intervention_id
                    )

            return ScoreImportCommitResult(
                assessment_id=preview.assessment_id,
                imported_count=imported_count,
                detected_intervention_count=(
                    len(detected_ids)
                ),
            )

    def _read_excel(
        self,
        path: Path,
    ) -> list[dict[str, Any]]:
        """
        READ:
        - chỉ đọc sheet đầu tiên;
        - dòng 1 là header;
        - bỏ qua dòng trống hoàn toàn.
        """
        try:
            workbook = load_workbook(
                filename=path,
                read_only=True,
                data_only=True,
            )
        except Exception as exc:
            raise ValidationError(
                "Không thể đọc file Excel."
            ) from exc

        try:
            worksheet = workbook.worksheets[0]

            header_values = [
                cell.value
                for cell in next(
                    worksheet.iter_rows(
                        min_row=1,
                        max_row=1,
                    )
                )
            ]

            header_map = self._build_header_map(
                header_values
            )

            rows: list[dict[str, Any]] = []

            for excel_row_number, cells in enumerate(
                worksheet.iter_rows(min_row=2),
                start=2,
            ):
                values = [
                    cell.value
                    for cell in cells
                ]

                if self._is_blank_row(values):
                    continue

                row_data: dict[str, Any] = {
                    "row_number": excel_row_number,
                }

                for field_name, column_index in (
                    header_map.items()
                ):
                    row_data[field_name] = (
                        values[column_index]
                        if column_index < len(values)
                        else None
                    )

                rows.append(row_data)

            return rows
        finally:
            workbook.close()

    def _build_header_map(
        self,
        headers: list[Any],
    ) -> dict[str, int]:
        mapped: dict[str, int] = {}

        for index, raw_header in enumerate(headers):
            normalized = self._normalize_header(
                raw_header
            )

            if not normalized:
                continue

            field_name = self.HEADER_ALIASES.get(
                normalized
            )

            if field_name is None:
                continue

            if field_name in mapped:
                raise ValidationError(
                    f"Cột '{raw_header}' bị trùng ý nghĩa "
                    "với một cột khác."
                )

            mapped[field_name] = index

        missing = (
            self.REQUIRED_HEADERS
            - set(mapped)
        )

        if missing:
            readable = {
                "student_code": "Mã học sinh",
                "score": "Điểm",
            }

            missing_text = ", ".join(
                readable[item]
                for item in sorted(missing)
            )

            raise ValidationError(
                "Thiếu cột bắt buộc: "
                f"{missing_text}."
            )

        return mapped

    def _build_preview_rows(
        self,
        connection,
        raw_rows: list[dict[str, Any]],
    ) -> list[ScoreImportPreviewRow]:
        result: list[ScoreImportPreviewRow] = []
        seen_student_codes: set[str] = set()

        for raw in raw_rows:
            errors: list[str] = []
            warnings: list[str] = []

            student_code = self._normalize_code(
                raw.get("student_code")
            )
            full_name = self._normalize_text(
                raw.get("full_name")
            )
            class_name = self._normalize_text(
                raw.get("class_name")
            )
            score = self._normalize_score(
                raw.get("score"),
                errors,
            )

            enrollment_id: int | None = None

            if not student_code:
                errors.append(
                    "Mã học sinh không được để trống."
                )
            elif student_code in seen_student_codes:
                errors.append(
                    "Mã học sinh bị lặp trong file import."
                )
            else:
                seen_student_codes.add(student_code)

            student = None

            if student_code:
                student = (
                    self.student_repository.get_by_code(
                        connection,
                        student_code,
                    )
                )

                if student is None:
                    errors.append(
                        "Không tìm thấy học sinh theo mã."
                    )

            if student is not None:
                if (
                    full_name
                    and self._compare_text(full_name)
                    != self._compare_text(
                        student.full_name
                    )
                ):
                    warnings.append(
                        "Họ tên trong Excel khác dữ liệu hệ thống."
                    )

                enrollment = (
                    self.enrollment_repository
                    .get_active_by_student(
                        connection,
                        student.student_id,
                    )
                )

                if enrollment is None:
                    errors.append(
                        "Học sinh không có enrollment ACTIVE."
                    )
                else:
                    enrollment_id = (
                        enrollment.enrollment_id
                    )

                    if class_name:
                        self._validate_class_name(
                            connection=connection,
                            student_id=student.student_id,
                            enrollment_id=enrollment_id,
                            excel_class_name=class_name,
                            errors=errors,
                        )

            result.append(
                ScoreImportPreviewRow(
                    row_number=raw["row_number"],
                    student_code=student_code,
                    full_name=full_name,
                    class_name=class_name,
                    score=score,
                    enrollment_id=enrollment_id,
                    errors=tuple(errors),
                    warnings=tuple(warnings),
                )
            )

        return result

    def _validate_class_name(
        self,
        connection,
        student_id: str,
        enrollment_id: int,
        excel_class_name: str,
        errors: list[str],
    ) -> None:
        """
        Dùng history đã có trong EnrollmentRepository để đối chiếu
        class_name của enrollment ACTIVE, tránh viết SQL trong service.
        """
        history = (
            self.enrollment_repository.list_by_student(
                connection,
                student_id,
            )
        )

        current = next(
            (
                item
                for item in history
                if item.enrollment_id
                == enrollment_id
            ),
            None,
        )

        if current is None:
            errors.append(
                "Không xác định được lớp hiện tại của học sinh."
            )
            return

        if (
            self._compare_text(current.class_name)
            != self._compare_text(excel_class_name)
        ):
            errors.append(
                "Lớp trong Excel không khớp lớp hiện tại "
                "của học sinh."
            )

    @staticmethod
    def _normalize_score(
        value: Any,
        errors: list[str],
    ) -> Decimal | None:
        if value is None:
            errors.append(
                "Điểm không được để trống."
            )
            return None

        if isinstance(value, bool):
            errors.append(
                "Điểm không hợp lệ."
            )
            return None

        text = str(value).strip()

        if not text:
            errors.append(
                "Điểm không được để trống."
            )
            return None

        text = text.replace(",", ".")

        try:
            score = Decimal(text)
        except (InvalidOperation, ValueError):
            errors.append(
                "Điểm không hợp lệ."
            )
            return None

        if (
            not score.is_finite()
            or score < Decimal("0")
            or score > Decimal("10")
        ):
            errors.append(
                "Điểm phải nằm trong khoảng từ 0 đến 10."
            )
            return None

        return score.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

    @classmethod
    def _normalize_header(
        cls,
        value: Any,
    ) -> str:
        return cls._compare_text(
            cls._normalize_text(value)
        )

    @staticmethod
    def _normalize_code(
        value: Any,
    ) -> str:
        if value is None:
            return ""

        return str(value).strip().upper()

    @staticmethod
    def _normalize_text(
        value: Any,
    ) -> str | None:
        if value is None:
            return None

        text = " ".join(
            str(value).strip().split()
        )

        return text or None

    @staticmethod
    def _compare_text(
        value: str | None,
    ) -> str:
        if not value:
            return ""

        return " ".join(
            value.strip().casefold().split()
        )

    @staticmethod
    def _is_blank_row(
        values: list[Any],
    ) -> bool:
        return all(
            value is None
            or (
                isinstance(value, str)
                and not value.strip()
            )
            for value in values
        )
