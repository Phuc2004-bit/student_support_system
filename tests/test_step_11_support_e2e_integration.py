from datetime import date
from decimal import Decimal
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QDate
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from app_context import AppContext
from config.database import db_settings
from database.connection import DatabaseManager
from exceptions import BusinessRuleError, InvalidStateTransitionError
from models.dto import StudentCreateData, UserSession
from models.enums import InterventionStatus, ReviewResult, UserRole
from repositories import (
    AcademicRepository,
    InterventionRepository,
    SupportRuleRepository,
    UserRepository,
)
from services import (
    AcademicService,
    EnrollmentService,
    ScoreService,
    StudentProfileService,
    StudentService,
    SupportService,
)
from services.permission_service import PermissionService
from services.report_service import ReportService
from services.user_service import UserService
from ui.dialogs.intervention_detail_dialog import InterventionDetailDialog
from ui.dialogs.intervention_plan_dialog import InterventionPlanDialog
from ui.dialogs.intervention_review_dialog import InterventionReviewDialog
from ui.main_window import MainWindow
from ui.pages.support_page import SupportPage


YEAR = "E11_2627"
CLASS = "E11_9A"
SUBJECT = "E11_M1"
TEACHER = "e11_teacher"
STUDENT_CODE = "E11_HS1"
TRIGGER = "E11_TRG"
REVIEW_1 = "E11_R1"
REVIEW_2 = "E11_R2"
THRESHOLD = Decimal("4.25")


def app():
    return QApplication.instance() or QApplication([])


def get_test_db():
    connection_string = db_settings.connection_string().replace(
        "DATABASE=student_support_db;",
        "DATABASE=student_support_db_test;",
    )
    assert "student_support_db_test" in connection_string
    return DatabaseManager(connection_string)


def cleanup(db):
    with db.transaction() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            DELETE FROM dbo.INTERVENTION_REVIEWS
            WHERE intervention_id IN
            (
                SELECT i.intervention_id
                FROM dbo.INTERVENTIONS i
                INNER JOIN dbo.STUDENT_ENROLLMENTS e
                    ON e.enrollment_id = i.enrollment_id
                INNER JOIN dbo.STUDENTS s ON s.student_id = e.student_id
                WHERE s.student_code = ?
            )
            """,
            STUDENT_CODE,
        )
        cursor.execute(
            """
            DELETE FROM dbo.INTERVENTIONS
            WHERE enrollment_id IN
            (
                SELECT e.enrollment_id
                FROM dbo.STUDENT_ENROLLMENTS e
                INNER JOIN dbo.STUDENTS s ON s.student_id = e.student_id
                WHERE s.student_code = ?
            )
            """,
            STUDENT_CODE,
        )
        cursor.execute(
            """
            DELETE FROM dbo.SCORES
            WHERE enrollment_id IN
            (
                SELECT e.enrollment_id
                FROM dbo.STUDENT_ENROLLMENTS e
                INNER JOIN dbo.STUDENTS s ON s.student_id = e.student_id
                WHERE s.student_code = ?
            )
            """,
            STUDENT_CODE,
        )
        cursor.execute(
            """
            DELETE FROM dbo.SUPPORT_RULES
            WHERE subject_id IN
            (
                SELECT subject_id FROM dbo.SUBJECTS
                WHERE subject_code = ?
            )
            """,
            SUBJECT,
        )
        cursor.execute(
            """
            DELETE FROM dbo.STUDENT_ENROLLMENTS
            WHERE student_id IN
            (
                SELECT student_id FROM dbo.STUDENTS
                WHERE student_code = ?
            )
            """,
            STUDENT_CODE,
        )
        cursor.execute(
            "DELETE FROM dbo.STUDENTS WHERE student_code = ?",
            STUDENT_CODE,
        )
        cursor.execute(
            """
            DELETE FROM dbo.ASSESSMENTS
            WHERE assessment_name IN (?, ?, ?)
            """,
            TRIGGER,
            REVIEW_1,
            REVIEW_2,
        )
        cursor.execute(
            "DELETE FROM dbo.CLASSES WHERE class_name = ?",
            CLASS,
        )
        cursor.execute(
            "DELETE FROM dbo.SUBJECTS WHERE subject_code = ?",
            SUBJECT,
        )
        cursor.execute(
            "DELETE FROM dbo.SCHOOL_YEARS WHERE year_name = ?",
            YEAR,
        )
        cursor.execute(
            "DELETE FROM dbo.USERS WHERE username = ?",
            TEACHER,
        )


def select(combo, value):
    index = combo.findData(value)
    assert index >= 0
    combo.setCurrentIndex(index)


def case_from_page(page, intervention_id):
    return next(
        (
            row for row in page.items
            if row.intervention_id == intervention_id
        ),
        None,
    )


def assert_filter(page, intervention_id, status, expected_status=None):
    select(page.status_combo, status)
    row = case_from_page(page, intervention_id)
    if expected_status is None:
        assert row is None
    else:
        assert row is not None
        assert row.status == expected_status.value


def count_workflow_rows(db, intervention_id, enrollment_id):
    with db.transaction() as connection:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM dbo.SCORES WHERE enrollment_id = ?",
            enrollment_id,
        )
        score_count = cursor.fetchone()[0]
        cursor.execute(
            """
            SELECT COUNT(*) FROM dbo.INTERVENTION_REVIEWS
            WHERE intervention_id = ?
            """,
            intervention_id,
        )
        review_count = cursor.fetchone()[0]
        cursor.execute(
            """
            SELECT COUNT(*) FROM dbo.INTERVENTIONS
            WHERE enrollment_id = ?
            """,
            enrollment_id,
        )
        intervention_count = cursor.fetchone()[0]
    return score_count, review_count, intervention_count


class CapturingDetailDialog(InterventionDetailDialog):
    last_instance = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        CapturingDetailDialog.last_instance = self

    def exec(self):
        return QDialog.DialogCode.Rejected


class AutoPlanDialog(InterventionPlanDialog):
    teacher_id = None

    def exec(self):
        select(self.responsible_combo, self.teacher_id)
        self.start_date_input.setDate(QDate(2026, 10, 20))
        self.support_method_input.setText("Phụ đạo nhóm nhỏ")
        self.notes_input.setPlainText("Theo dõi hai vòng đánh giá")
        assert self.save_plan() is True
        return self.result()


class AutoReviewDialog(InterventionReviewDialog):
    inputs = []

    def exec(self):
        assessment_id, score, review_date, notes = self.inputs.pop(0)
        select(self.assessment_combo, assessment_id)
        self.score_input.setText(score)
        self.review_date_input.setDate(QDate(review_date))
        self.notes_input.setPlainText(notes)
        assert self.save_review() is True
        return self.result()


class FailedReviewDialog(InterventionReviewDialog):
    assessment_id = None
    save_result = None

    def exec(self):
        select(self.assessment_combo, self.assessment_id)
        self.score_input.setText("3.10")
        self.review_date_input.setDate(QDate(2026, 11, 14))
        self.notes_input.setPlainText("Phải rollback")
        FailedReviewDialog.save_result = self.save_review()
        return QDialog.DialogCode.Rejected


def test_support_workflow_end_to_end(monkeypatch):
    app()
    db = get_test_db()
    academic_repository = AcademicRepository()
    intervention_repository = InterventionRepository()
    rule_repository = SupportRuleRepository()
    academic_service = AcademicService(db)
    report_service = ReportService(db)
    support_service = SupportService(db)
    score_service = ScoreService(db)
    profile_service = StudentProfileService(db)
    user_service = UserService(db)
    cleanup(db)

    try:
        with db.transaction() as connection:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT grade_id FROM dbo.GRADES WHERE grade_number = ?",
                9,
            )
            grade_row = cursor.fetchone()
            if grade_row is None:
                cursor.execute(
                    """
                    INSERT INTO dbo.GRADES (grade_number, grade_name)
                    OUTPUT INSERTED.grade_id VALUES (?, ?)
                    """,
                    9,
                    "Khối 9",
                )
                grade_id = cursor.fetchone()[0]
            else:
                grade_id = grade_row[0]

            year_id = academic_repository.create_school_year(
                connection,
                YEAR,
                date(2026, 9, 1),
                date(2027, 5, 31),
                False,
            )
            class_id = academic_repository.create_class(
                connection,
                CLASS,
                grade_id,
                year_id,
            )
            subject_id = academic_repository.create_subject(
                connection,
                SUBJECT,
                "Môn Support E2E",
            )
            trigger_assessment = academic_repository.create_assessment(
                connection,
                subject_id,
                year_id,
                TRIGGER,
                1,
                "MIDTERM",
                date(2026, 10, 10),
            )
            review_1_assessment = academic_repository.create_assessment(
                connection,
                subject_id,
                year_id,
                REVIEW_1,
                1,
                "REVIEW",
                date(2026, 11, 15),
            )
            review_2_assessment = academic_repository.create_assessment(
                connection,
                subject_id,
                year_id,
                REVIEW_2,
                1,
                "REVIEW",
                date(2026, 12, 15),
            )
            rule = rule_repository.create(
                connection,
                subject_id,
                year_id,
                THRESHOLD,
            )
            teacher = UserRepository().create(
                connection,
                TEACHER,
                "$2b$12$e2e",
                "Giáo viên Support E2E",
                UserRole.TEACHER,
            )

        student = StudentService(db).create_student(StudentCreateData(
            student_code=STUDENT_CODE,
            full_name="Học sinh Support E2E",
        ))
        enrollment = EnrollmentService(db).enroll_student(
            student.student_id,
            class_id,
            date(2026, 9, 1),
        )
        trigger_score = score_service.create_score(
            enrollment.enrollment_id,
            trigger_assessment.assessment_id,
            Decimal("3.25"),
        )
        intervention = support_service.detect_from_score(
            trigger_score.score_id
        )
        assert intervention.status is InterventionStatus.DETECTED

        context = AppContext(
            db=db,
            auth_service=object(),
            permission_service=PermissionService(),
            session=UserSession(
                teacher.user_id,
                teacher.username,
                teacher.full_name,
                UserRole.ADMIN,
            ),
            academic_service=academic_service,
            report_service=report_service,
            support_service=support_service,
            user_service=user_service,
            score_service=score_service,
            student_profile_service=profile_service,
        )
        window = MainWindow(context)
        window.navigate_to("support")
        page = window.pages["support"]
        assert isinstance(page, SupportPage)
        select(page.school_year_combo, year_id)
        select(page.grade_combo, grade_id)
        select(page.class_combo, class_id)
        select(page.subject_combo, subject_id)

        assert_filter(
            page,
            intervention.intervention_id,
            InterventionStatus.DETECTED,
            InterventionStatus.DETECTED,
        )
        select(page.status_combo, None)
        assert case_from_page(page, intervention.intervention_id).status == (
            InterventionStatus.DETECTED.value
        )

        page.detail_dialog_factory = CapturingDetailDialog
        assert page.open_intervention_detail(
            intervention.intervention_id
        ) is True
        dialog = CapturingDetailDialog.last_instance
        assert dialog.intervention_id == intervention.intervention_id
        assert dialog.detail.student_code == STUDENT_CODE
        assert dialog.detail.class_name == CLASS
        assert dialog.detail.school_year_name == YEAR
        assert dialog.detail.subject_name == "Môn Support E2E"
        assert dialog.detail.trigger_score == Decimal("3.25")

        with pytest.raises(InvalidStateTransitionError):
            support_service.start_intervention(intervention.intervention_id)

        AutoPlanDialog.teacher_id = teacher.user_id
        dialog.plan_dialog_factory = AutoPlanDialog
        assert dialog.open_plan_dialog() is True
        planned = support_service.get_intervention_detail(
            intervention.intervention_id
        )
        assert planned.status is InterventionStatus.PLANNED
        assert planned.responsible_user_id == teacher.user_id
        assert planned.support_method == "Phụ đạo nhóm nhỏ"
        assert planned.notes == "Theo dõi hai vòng đánh giá"
        assert planned.trigger_score_id == trigger_score.score_id
        assert planned.reviews == ()
        assert_filter(
            page,
            intervention.intervention_id,
            InterventionStatus.DETECTED,
        )
        assert_filter(
            page,
            intervention.intervention_id,
            InterventionStatus.PLANNED,
            InterventionStatus.PLANNED,
        )
        with pytest.raises(InvalidStateTransitionError):
            support_service.review_intervention(
                intervention.intervention_id,
                trigger_score.score_id,
                date(2026, 10, 21),
            )

        for module in (
            "ui.dialogs.intervention_start_confirmation.QMessageBox.question",
            "ui.dialogs.intervention_waiting_review_confirmation."
            "QMessageBox.question",
            "ui.dialogs.intervention_continue_confirmation.QMessageBox.question",
        ):
            monkeypatch.setattr(
                module,
                lambda *_args, **_kwargs: QMessageBox.StandardButton.Yes,
            )

        counts_before_start = count_workflow_rows(
            db,
            intervention.intervention_id,
            enrollment.enrollment_id,
        )
        assert dialog.begin_planned_support() is True
        in_progress = support_service.get_intervention_detail(
            intervention.intervention_id
        )
        assert in_progress.status is InterventionStatus.IN_PROGRESS
        assert in_progress.trigger_score_id == planned.trigger_score_id
        assert in_progress.responsible_user_id == planned.responsible_user_id
        assert in_progress.support_method == planned.support_method
        assert in_progress.notes == planned.notes
        assert in_progress.start_date == planned.start_date
        assert count_workflow_rows(
            db,
            intervention.intervention_id,
            enrollment.enrollment_id,
        ) == counts_before_start
        assert_filter(
            page,
            intervention.intervention_id,
            InterventionStatus.PLANNED,
        )
        assert_filter(
            page,
            intervention.intervention_id,
            InterventionStatus.IN_PROGRESS,
            InterventionStatus.IN_PROGRESS,
        )
        with pytest.raises(InvalidStateTransitionError):
            support_service.plan_intervention(
                intervention.intervention_id,
                teacher.user_id,
                date(2026, 10, 20),
            )

        assert dialog.move_to_review_queue() is True
        waiting = support_service.get_intervention_detail(
            intervention.intervention_id
        )
        assert waiting.status is InterventionStatus.WAITING_REVIEW
        assert waiting.reviews == ()
        assert_filter(
            page,
            intervention.intervention_id,
            InterventionStatus.IN_PROGRESS,
        )
        assert_filter(
            page,
            intervention.intervention_id,
            InterventionStatus.WAITING_REVIEW,
            InterventionStatus.WAITING_REVIEW,
        )
        with pytest.raises(InvalidStateTransitionError):
            support_service.continue_intervention(
                intervention.intervention_id
            )

        counts_before_failed_review = count_workflow_rows(
            db,
            intervention.intervention_id,
            enrollment.enrollment_id,
        )
        with db.transaction() as connection:
            rule_repository.set_active(connection, rule.rule_id, False)
        FailedReviewDialog.assessment_id = review_1_assessment.assessment_id
        FailedReviewDialog.save_result = None
        dialog.review_dialog_factory = FailedReviewDialog
        assert dialog.open_review_dialog() is False
        assert FailedReviewDialog.save_result is False
        assert count_workflow_rows(
            db,
            intervention.intervention_id,
            enrollment.enrollment_id,
        ) == counts_before_failed_review
        assert support_service.get_intervention_detail(
            intervention.intervention_id
        ).status is InterventionStatus.WAITING_REVIEW
        with db.transaction() as connection:
            rule_repository.set_active(connection, rule.rule_id, True)

        AutoReviewDialog.inputs = [(
            review_1_assessment.assessment_id,
            "4.10",
            date(2026, 11, 15),
            "Chưa đạt ngưỡng cấu hình",
        )]
        dialog.review_dialog_factory = AutoReviewDialog
        assert dialog.open_review_dialog() is True
        after_review_1 = support_service.get_intervention_detail(
            intervention.intervention_id
        )
        assert after_review_1.status is InterventionStatus.CONTINUE
        assert [item.result for item in after_review_1.reviews] == [
            ReviewResult.NOT_PASSED
        ]
        review_score_1_id = after_review_1.reviews[0].score_id
        assert_filter(
            page,
            intervention.intervention_id,
            InterventionStatus.WAITING_REVIEW,
        )
        assert_filter(
            page,
            intervention.intervention_id,
            InterventionStatus.CONTINUE,
            InterventionStatus.CONTINUE,
        )

        with pytest.raises(InvalidStateTransitionError):
            support_service.start_intervention(intervention.intervention_id)
        counts_before_continue = count_workflow_rows(
            db,
            intervention.intervention_id,
            enrollment.enrollment_id,
        )
        assert dialog.resume_support() is True
        assert count_workflow_rows(
            db,
            intervention.intervention_id,
            enrollment.enrollment_id,
        ) == counts_before_continue
        after_continue = support_service.get_intervention_detail(
            intervention.intervention_id
        )
        assert after_continue.status is InterventionStatus.IN_PROGRESS
        assert after_continue.reviews == after_review_1.reviews
        assert_filter(
            page,
            intervention.intervention_id,
            InterventionStatus.CONTINUE,
        )
        assert_filter(
            page,
            intervention.intervention_id,
            InterventionStatus.IN_PROGRESS,
            InterventionStatus.IN_PROGRESS,
        )

        assert dialog.move_to_review_queue() is True
        AutoReviewDialog.inputs = [(
            review_2_assessment.assessment_id,
            "4.25",
            date(2026, 12, 15),
            "Đã đạt đúng ngưỡng cấu hình",
        )]
        dialog.review_dialog_factory = AutoReviewDialog
        assert dialog.open_review_dialog() is True
        completed = support_service.get_intervention_detail(
            intervention.intervention_id
        )
        assert completed.status is InterventionStatus.COMPLETED
        assert completed.intervention_id == intervention.intervention_id
        assert completed.trigger_score_id == trigger_score.score_id
        assert [item.result for item in completed.reviews] == [
            ReviewResult.NOT_PASSED,
            ReviewResult.PASSED,
        ]
        assert [item.review_date for item in completed.reviews] == [
            date(2026, 11, 15),
            date(2026, 12, 15),
        ]
        assert completed.reviews[0].score_id == review_score_1_id
        review_score_2_id = completed.reviews[1].score_id

        assert_filter(
            page,
            intervention.intervention_id,
            InterventionStatus.WAITING_REVIEW,
        )
        assert_filter(
            page,
            intervention.intervention_id,
            InterventionStatus.COMPLETED,
            InterventionStatus.COMPLETED,
        )
        select(page.status_combo, None)
        assert case_from_page(page, intervention.intervention_id).status == (
            InterventionStatus.COMPLETED.value
        )

        dialog.load_detail()
        for button_name in (
            "plan_button",
            "start_button",
            "waiting_review_button",
            "review_button",
            "continue_button",
        ):
            assert getattr(dialog, button_name).isHidden()
        assert not hasattr(dialog, "complete_button")

        profile = profile_service.get_profile(student.student_id)
        assert [item.score_id for item in profile.score_history] == [
            trigger_score.score_id,
            review_score_1_id,
            review_score_2_id,
        ]
        assert [item.score for item in profile.score_history] == [
            Decimal("3.25"),
            Decimal("4.10"),
            Decimal("4.25"),
        ]
        assert len(profile.intervention_history) == 1
        assert profile.intervention_history[0].intervention_id == (
            intervention.intervention_id
        )
        assert profile.intervention_history[0].status is (
            InterventionStatus.COMPLETED
        )

        for score_id in (
            trigger_score.score_id,
            review_score_1_id,
            review_score_2_id,
        ):
            assert score_service.can_edit_score(score_id) is False
            with pytest.raises(BusinessRuleError):
                score_service.update_score(score_id, Decimal("9.00"))

        completed_attempts = (
            lambda: support_service.plan_intervention(
                intervention.intervention_id,
                teacher.user_id,
                date(2026, 10, 20),
            ),
            lambda: support_service.start_intervention(
                intervention.intervention_id
            ),
            lambda: support_service.mark_waiting_review(
                intervention.intervention_id
            ),
            lambda: support_service.continue_intervention(
                intervention.intervention_id
            ),
            lambda: support_service.review_intervention(
                intervention.intervention_id,
                review_score_2_id,
                date(2026, 12, 16),
            ),
        )
        for attempt in completed_attempts:
            with pytest.raises(InvalidStateTransitionError):
                attempt()

        teacher_window = MainWindow(AppContext(
            db=db,
            auth_service=object(),
            permission_service=PermissionService(),
            session=UserSession(
                teacher.user_id,
                teacher.username,
                teacher.full_name,
                UserRole.TEACHER,
            ),
            academic_service=academic_service,
            report_service=report_service,
            support_service=support_service,
            user_service=user_service,
        ))
        teacher_window.navigate_to("support")
        assert teacher_window.can_navigate_to("support") is True
        assert isinstance(teacher_window.pages["support"], SupportPage)

        window.request_logout()
        assert context.session is None
    finally:
        cleanup(db)
