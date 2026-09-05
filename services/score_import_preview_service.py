from __future__ import annotations

from collections import Counter, defaultdict

import pyodbc

from database.connection import DatabaseManager
from exceptions import DatabaseError, ScoreImportError, ValidationError
from models.dto.score_import import (
    ScoreImportContext,
    ScoreImportIssue,
    ScoreImportIssueSeverity,
    ScoreImportPreview,
    ScoreImportPreviewRow,
    ScoreImportWorkbook,
)
from models.enums import AssessmentStatus, EnrollmentStatus
from repositories import (
    AcademicRepository,
    EnrollmentRepository,
    ScoreRepository,
    StudentRepository,
)
from services.score_service import ScoreService


class ScoreImportPreviewService:
    """Build a read-only, all-or-nothing score import preview."""

    def __init__(
        self,
        db: DatabaseManager,
        academic_repository: AcademicRepository | None = None,
        student_repository: StudentRepository | None = None,
        enrollment_repository: EnrollmentRepository | None = None,
        score_repository: ScoreRepository | None = None,
    ) -> None:
        self.db = db
        self.academic_repository = academic_repository or AcademicRepository()
        self.student_repository = student_repository or StudentRepository()
        self.enrollment_repository = enrollment_repository or EnrollmentRepository()
        self.score_repository = score_repository or ScoreRepository()

    def preview_import(
        self,
        context: ScoreImportContext,
        workbook: ScoreImportWorkbook,
    ) -> ScoreImportPreview:
        self._validate_input(context, workbook)
        student_ids = tuple(
            dict.fromkeys(row.student_id for row in workbook.rows if row.student_id)
        )
        try:
            with self.db.transaction() as connection:
                self._validate_context(connection, context)
                students = self.student_repository.list_by_ids(
                    connection, student_ids
                )
                enrollments = self.enrollment_repository.list_by_student_ids(
                    connection, student_ids
                )
                roster = self.score_repository.list_by_class_assessment(
                    connection,
                    context.class_id,
                    context.school_year_id,
                    context.assessment_id,
                    EnrollmentStatus.ACTIVE,
                )
        except pyodbc.Error as exc:
            raise DatabaseError(
                "Không thể đọc dữ liệu để kiểm tra file nhập điểm."
            ) from exc

        students_by_id = {student.student_id: student for student in students}
        enrollments_by_student = defaultdict(list)
        for enrollment in enrollments:
            enrollments_by_student[enrollment.student_id].append(enrollment)
        roster_by_student = {item.student_id: item for item in roster}
        duplicate_ids = {
            student_id
            for student_id, count in Counter(
                row.student_id for row in workbook.rows if row.student_id
            ).items()
            if count > 1
        }

        preview_rows = tuple(
            self._preview_row(
                context,
                row,
                students_by_id,
                enrollments_by_student,
                roster_by_student,
                duplicate_ids,
            )
            for row in workbook.rows
        )
        return ScoreImportPreview(context=context, rows=preview_rows)

    @staticmethod
    def _validate_input(context, workbook) -> None:
        if not isinstance(context, ScoreImportContext):
            raise ScoreImportError("Ngữ cảnh preview nhập điểm không hợp lệ.")
        if not isinstance(workbook, ScoreImportWorkbook):
            raise ScoreImportError("Dữ liệu workbook nhập điểm không hợp lệ.")
        for name in (
            "school_year_id",
            "class_id",
            "subject_id",
            "assessment_id",
        ):
            value = getattr(context, name)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ScoreImportError(f"{name} không hợp lệ.")

    def _validate_context(self, connection, context: ScoreImportContext) -> None:
        year = self.academic_repository.get_school_year_by_id(
            connection, context.school_year_id
        )
        if year is None:
            raise ScoreImportError("Không tìm thấy năm học đã chọn.")

        school_class = self.academic_repository.get_class_by_id(
            connection, context.class_id
        )
        if school_class is None:
            raise ScoreImportError("Không tìm thấy lớp đã chọn.")
        if int(school_class[4]) != context.school_year_id:
            raise ScoreImportError("Lớp không thuộc năm học đã chọn.")

        subject = self.academic_repository.get_subject_by_id(
            connection, context.subject_id
        )
        if subject is None:
            raise ScoreImportError("Không tìm thấy môn học đã chọn.")
        if not subject.is_active:
            raise ScoreImportError("Môn học đã chọn không còn hoạt động.")

        assessment = self.academic_repository.get_assessment_by_id(
            connection, context.assessment_id
        )
        if assessment is None:
            raise ScoreImportError("Không tìm thấy bài đánh giá đã chọn.")
        if assessment.status != AssessmentStatus.ACTIVE:
            raise ScoreImportError("Bài đánh giá đã chọn không còn hoạt động.")
        if assessment.school_year_id != context.school_year_id:
            raise ScoreImportError("Bài đánh giá không thuộc năm học đã chọn.")
        if assessment.subject_id != context.subject_id:
            raise ScoreImportError("Bài đánh giá không thuộc môn học đã chọn.")

    @staticmethod
    def _preview_row(
        context,
        row,
        students_by_id,
        enrollments_by_student,
        roster_by_student,
        duplicate_ids,
    ) -> ScoreImportPreviewRow:
        issues = list(row.issues)
        student = students_by_id.get(row.student_id)
        roster_item = roster_by_student.get(row.student_id)
        resolved_enrollment_id = None

        if row.student_id in duplicate_ids:
            issues.append(ScoreImportIssue(
                "DUPLICATE_FILE_ROW", "student_id",
                "Học sinh xuất hiện nhiều lần trong file nhập điểm.",
            ))

        if row.student_id and student is None:
            issues.append(ScoreImportIssue(
                "UNKNOWN_STUDENT", "student_id",
                "Không tìm thấy học sinh.",
            ))
        elif student is not None:
            if row.student_name and ScoreImportPreviewService._name_key(
                row.student_name
            ) != ScoreImportPreviewService._name_key(student.full_name):
                issues.append(ScoreImportIssue(
                    "STUDENT_NAME_MISMATCH", "student_name",
                    "Họ tên trong Excel khác dữ liệu hệ thống.",
                    ScoreImportIssueSeverity.WARNING,
                ))

            student_enrollments = enrollments_by_student.get(row.student_id, ())
            year_enrollments = [
                item for item in student_enrollments
                if item.school_year_id == context.school_year_id
            ]
            class_enrollments = [
                item for item in year_enrollments
                if item.class_id == context.class_id
            ]
            active_context = [
                item for item in class_enrollments
                if item.status == EnrollmentStatus.ACTIVE
            ]
            if not student_enrollments:
                issues.append(ScoreImportIssue(
                    "MISSING_ENROLLMENT", "student_id",
                    "Học sinh chưa có enrollment.",
                ))
            elif not year_enrollments:
                issues.append(ScoreImportIssue(
                    "ENROLLMENT_WRONG_YEAR", "student_id",
                    "Học sinh không có enrollment trong năm học đã chọn.",
                ))
            elif not class_enrollments:
                issues.append(ScoreImportIssue(
                    "ENROLLMENT_WRONG_CLASS", "student_id",
                    "Học sinh không thuộc lớp đã chọn.",
                ))
            elif not active_context:
                issues.append(ScoreImportIssue(
                    "ENROLLMENT_NOT_ACTIVE", "student_id",
                    "Enrollment trong lớp đã chọn không ở trạng thái ACTIVE.",
                ))
            elif len(active_context) > 1:
                issues.append(ScoreImportIssue(
                    "AMBIGUOUS_ENROLLMENT", "student_id",
                    "Học sinh có nhiều enrollment ACTIVE trong cùng ngữ cảnh.",
                ))
            else:
                resolved_enrollment_id = active_context[0].enrollment_id

        normalized_score = None
        if not any(issue.field == "score" for issue in issues):
            try:
                normalized_score = ScoreService.normalize_score_value(
                    row.normalized_score
                )
            except ValidationError as exc:
                issues.append(ScoreImportIssue(
                    "INVALID_SCORE", "score", str(exc),
                ))

        if roster_item is not None and roster_item.score_id is not None:
            issues.append(ScoreImportIssue(
                "DUPLICATE_DATABASE_SCORE", "score",
                "Học sinh đã có điểm cho bài đánh giá này.",
            ))

        return ScoreImportPreviewRow(
            row_number=row.row_number,
            student_id=row.student_id,
            student_name_excel=row.student_name,
            student_name_db=student.full_name if student is not None else None,
            enrollment_id=resolved_enrollment_id,
            normalized_score=normalized_score,
            issues=tuple(issues),
        )

    @staticmethod
    def _name_key(value: str) -> str:
        return " ".join(value.casefold().split())
