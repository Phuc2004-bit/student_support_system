import os
from datetime import date
from decimal import Decimal

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from app_context import AppContext
from config.database import db_settings
from database.connection import DatabaseManager
from exceptions import BusinessRuleError, DuplicateError
from models.dto import StudentCreateData, UserSession
from models.enums import InterventionStatus, UserRole
from repositories import AcademicRepository, SupportRuleRepository, UserRepository
from services import (
    AcademicService,
    EnrollmentService,
    ScoreService,
    StudentProfileService,
    StudentService,
    SupportService,
)
from services.permission_service import PermissionService
from ui.main_window import MainWindow
from ui.pages.scores_page import ScoresPage


YEAR = "E10_2627"
CLASS = "E10_A"
OTHER_CLASS = "E10_B"
SUBJECT = "E10_M1"
NO_RULE_SUBJECT = "E10_M2"
TEACHER = "e10_teacher"
STUDENT_CODES = ("E10_A1", "E10_B1", "E10_C1", "E10_X1")
ASSESSMENTS = ("E10_S1", "E10_S2", "E10_S3", "E10_R1", "E10_S4")
NO_RULE_ASSESSMENT = "E10_FAIL"
THRESHOLD = Decimal("4.25")


def app():
    return QApplication.instance() or QApplication([])


def get_test_db():
    connection_string = db_settings.connection_string().replace(
        "DATABASE=student_support_db;",
        "DATABASE=student_support_db_test;",
    )
    return DatabaseManager(connection_string)


def cleanup(db):
    with db.transaction() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """DELETE FROM dbo.INTERVENTION_REVIEWS
               WHERE intervention_id IN
               (SELECT i.intervention_id FROM dbo.INTERVENTIONS i
                INNER JOIN dbo.STUDENT_ENROLLMENTS e
                    ON e.enrollment_id = i.enrollment_id
                INNER JOIN dbo.STUDENTS s ON s.student_id = e.student_id
                WHERE s.student_code LIKE ?)""",
            "E10_%",
        )
        cursor.execute(
            """DELETE FROM dbo.INTERVENTIONS
               WHERE enrollment_id IN
               (SELECT e.enrollment_id FROM dbo.STUDENT_ENROLLMENTS e
                INNER JOIN dbo.STUDENTS s ON s.student_id = e.student_id
                WHERE s.student_code LIKE ?)""",
            "E10_%",
        )
        cursor.execute(
            """DELETE FROM dbo.SCORES
               WHERE enrollment_id IN
               (SELECT e.enrollment_id FROM dbo.STUDENT_ENROLLMENTS e
                INNER JOIN dbo.STUDENTS s ON s.student_id = e.student_id
                WHERE s.student_code LIKE ?)""",
            "E10_%",
        )
        cursor.execute(
            """DELETE FROM dbo.SUPPORT_RULES
               WHERE subject_id IN
               (SELECT subject_id FROM dbo.SUBJECTS
                WHERE subject_code IN (?, ?))""",
            SUBJECT,
            NO_RULE_SUBJECT,
        )
        cursor.execute(
            """DELETE FROM dbo.STUDENT_ENROLLMENTS
               WHERE student_id IN
               (SELECT student_id FROM dbo.STUDENTS
                WHERE student_code LIKE ?)""",
            "E10_%",
        )
        cursor.execute(
            "DELETE FROM dbo.STUDENTS WHERE student_code LIKE ?",
            "E10_%",
        )
        cursor.execute(
            """DELETE FROM dbo.ASSESSMENTS
               WHERE assessment_name IN (?, ?, ?, ?, ?, ?)""",
            *ASSESSMENTS,
            NO_RULE_ASSESSMENT,
        )
        cursor.execute(
            "DELETE FROM dbo.CLASSES WHERE class_name IN (?, ?)",
            CLASS,
            OTHER_CLASS,
        )
        cursor.execute(
            "DELETE FROM dbo.SUBJECTS WHERE subject_code IN (?, ?)",
            SUBJECT,
            NO_RULE_SUBJECT,
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


def select_context(page, year_id, grade_id, class_id, subject_id, assessment_id):
    select(page.school_year_combo, year_id)
    select(page.grade_combo, grade_id)
    select(page.class_combo, class_id)
    select(page.subject_combo, subject_id)
    select(page.assessment_combo, assessment_id)


def row_by_code(page, student_code):
    for row in range(page.score_table.rowCount()):
        if page.score_table.item(row, 1).text() == student_code:
            return row
    raise AssertionError(f"Không tìm thấy học sinh {student_code} trong roster")


def input_score(page, student_code, value):
    page.score_table.item(row_by_code(page, student_code), 3).setText(value)


def test_scores_assessments_end_to_end():
    app()
    db = get_test_db()
    academic_repository = AcademicRepository()
    academic_service = AcademicService(db)
    student_service = StudentService(db)
    enrollment_service = EnrollmentService(db)
    score_service = ScoreService(db)
    support_service = SupportService(db)
    profile_service = StudentProfileService(db)
    cleanup(db)

    try:
        with db.transaction() as connection:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT grade_id FROM dbo.GRADES WHERE grade_number = ?",
                8,
            )
            grade_row = cursor.fetchone()
            if grade_row is None:
                cursor.execute(
                    """INSERT INTO dbo.GRADES (grade_number, grade_name)
                       OUTPUT INSERTED.grade_id VALUES (?, ?)""",
                    8,
                    "Khối 8",
                )
                grade_id = cursor.fetchone()[0]
            else:
                grade_id = grade_row[0]

            year_id = academic_repository.create_school_year(
                connection, YEAR, date(2026, 9, 1), date(2027, 5, 31), False
            )
            class_id = academic_repository.create_class(
                connection, CLASS, grade_id, year_id
            )
            other_class_id = academic_repository.create_class(
                connection, OTHER_CLASS, grade_id, year_id
            )
            subject_id = academic_repository.create_subject(
                connection, SUBJECT, "Môn E2E chính"
            )
            no_rule_subject_id = academic_repository.create_subject(
                connection, NO_RULE_SUBJECT, "Môn E2E rollback"
            )
            assessments = [
                academic_repository.create_assessment(
                    connection, subject_id, year_id, name, 1, kind,
                    date(2026, month, day),
                )
                for name, kind, month, day in (
                    (ASSESSMENTS[0], "QUIZ", 9, 10),
                    (ASSESSMENTS[1], "QUIZ", 9, 20),
                    (ASSESSMENTS[2], "QUIZ", 10, 1),
                    (ASSESSMENTS[3], "REVIEW", 10, 10),
                    (ASSESSMENTS[4], "QUIZ", 10, 20),
                )
            ]
            no_rule_assessment = academic_repository.create_assessment(
                connection, no_rule_subject_id, year_id,
                NO_RULE_ASSESSMENT, 1, "QUIZ", date(2026, 11, 1)
            )
            SupportRuleRepository().create(
                connection, subject_id, year_id, THRESHOLD, True
            )
            teacher = UserRepository().create(
                connection, TEACHER, "$2b$12$fakehash",
                "Giáo viên E2E", UserRole.TEACHER,
            )

        students = [
            student_service.create_student(StudentCreateData(code, name))
            for code, name in zip(
                STUDENT_CODES,
                ("An E2E", "Bình E2E", "Chi E2E", "Ngoài lớp E2E"),
            )
        ]
        enrollments = [
            enrollment_service.enroll_student(
                student.student_id,
                other_class_id if index == 3 else class_id,
                date(2026, 9, 1),
            )
            for index, student in enumerate(students)
        ]

        context = AppContext(
            db=db,
            auth_service=object(),
            permission_service=PermissionService(),
            session=UserSession(1, "admin", "Admin E2E", UserRole.ADMIN),
            academic_service=academic_service,
            enrollment_service=enrollment_service,
            student_profile_service=profile_service,
            score_service=score_service,
        )
        window = MainWindow(context)
        window.navigate_to("scores")
        page = window.pages["scores"]
        assert isinstance(page, ScoresPage)

        select_context(
            page, year_id, grade_id, class_id, subject_id,
            assessments[0].assessment_id,
        )
        assert page.score_table.rowCount() == 3
        assert {
            page.score_table.item(row, 1).text()
            for row in range(page.score_table.rowCount())
        } == set(STUDENT_CODES[:3])

        input_score(page, STUDENT_CODES[0], "8.00")
        input_score(page, STUDENT_CODES[1], "4.24")
        input_score(page, STUDENT_CODES[2], "4.25")
        assert page.save_scores() is True
        assert "Có 1 học sinh" in page.context_status_label.text()
        assert {
            row.student_code: row.score for row in page.score_rows
        } == {
            STUDENT_CODES[0]: Decimal("8.00"),
            STUDENT_CODES[1]: Decimal("4.24"),
            STUDENT_CODES[2]: Decimal("4.25"),
        }

        first_scores = {row.student_code: row for row in page.score_rows}
        a_score = first_scores[STUDENT_CODES[0]]
        b_score = first_scores[STUDENT_CODES[1]]
        first_case = support_service.get_open_intervention(
            enrollments[1].enrollment_id, subject_id
        )
        assert first_case.status == InterventionStatus.DETECTED
        assert first_case.enrollment_id == enrollments[1].enrollment_id
        assert first_case.subject_id == subject_id
        assert first_case.trigger_score_id == b_score.score_id
        assert support_service.get_open_intervention(
            enrollments[0].enrollment_id, subject_id
        ) is None
        assert support_service.get_open_intervention(
            enrollments[2].enrollment_id, subject_id
        ) is None

        b_row = row_by_code(page, STUDENT_CODES[1])
        page.score_table.selectRow(b_row)
        assert score_service.can_edit_score(b_score.score_id) is False
        assert page.begin_edit_selected_score() is False
        with pytest.raises(BusinessRuleError):
            score_service.update_score(b_score.score_id, Decimal("7"))

        a_row = row_by_code(page, STUDENT_CODES[0])
        page.score_table.selectRow(a_row)
        assert score_service.can_edit_score(a_score.score_id) is True
        assert page.begin_edit_selected_score() is True
        page.score_table.item(a_row, 3).setText("9.25")
        assert page.save_score_edit() is True
        updated_a = score_service.get_score(a_score.score_id)
        assert updated_a.score_id == a_score.score_id
        assert updated_a.enrollment_id == a_score.enrollment_id
        assert updated_a.assessment_id == a_score.assessment_id
        assert updated_a.score == Decimal("9.25")

        with pytest.raises(DuplicateError):
            score_service.create_score(
                b_score.enrollment_id, b_score.assessment_id, Decimal("6")
            )
        assert score_service.get_score(b_score.score_id).score == Decimal("4.24")

        select(page.assessment_combo, assessments[1].assessment_id)
        input_score(page, STUDENT_CODES[1], "3.75")
        assert page.save_scores() is True
        assert len(profile_service.get_profile(students[1].student_id).intervention_history) == 1

        support_service.plan_intervention(
            first_case.intervention_id, teacher.user_id,
            date(2026, 9, 25), "Phụ đạo E2E",
        )
        support_service.start_intervention(first_case.intervention_id)

        select(page.assessment_combo, assessments[2].assessment_id)
        input_score(page, STUDENT_CODES[1], "8.50")
        assert page.save_scores() is True
        assert support_service.get_open_intervention(
            enrollments[1].enrollment_id, subject_id
        ).status == InterventionStatus.IN_PROGRESS

        support_service.mark_waiting_review(first_case.intervention_id)
        select(page.assessment_combo, assessments[3].assessment_id)
        input_score(page, STUDENT_CODES[1], "8.75")
        assert page.save_scores() is True
        review_score = next(
            row for row in page.score_rows if row.student_code == STUDENT_CODES[1]
        )
        assert support_service.get_open_intervention(
            enrollments[1].enrollment_id, subject_id
        ).status == InterventionStatus.WAITING_REVIEW
        completed = support_service.review_intervention(
            first_case.intervention_id, review_score.score_id,
            date(2026, 10, 10), "Đạt E2E",
        )
        assert completed.status == InterventionStatus.COMPLETED

        select(page.assessment_combo, assessments[4].assessment_id)
        input_score(page, STUDENT_CODES[1], "3.25")
        assert page.save_scores() is True
        second_case = support_service.get_open_intervention(
            enrollments[1].enrollment_id, subject_id
        )
        assert second_case.intervention_id != first_case.intervention_id
        assert second_case.status == InterventionStatus.DETECTED

        profile = profile_service.get_profile(students[1].student_id)
        assert [item.assessment_name for item in profile.score_history] == list(ASSESSMENTS)
        assert [item.score for item in profile.score_history] == [
            Decimal("4.24"), Decimal("3.75"), Decimal("8.50"),
            Decimal("8.75"), Decimal("3.25"),
        ]
        assert [item.status for item in profile.intervention_history] == [
            InterventionStatus.COMPLETED,
            InterventionStatus.DETECTED,
        ]

        select(page.subject_combo, no_rule_subject_id)
        select(page.assessment_combo, no_rule_assessment.assessment_id)
        input_score(page, STUDENT_CODES[0], "9.00")
        input_score(page, STUDENT_CODES[2], "2.00")
        assert page.save_scores() is False
        assert "quy tắc bổ trợ" in page.context_status_label.text()
        failed_roster = score_service.list_score_roster(
            class_id, year_id, no_rule_subject_id,
            no_rule_assessment.assessment_id,
        )
        assert all(row.score_id is None for row in failed_roster)
        assert bool(
            page.score_table.item(row_by_code(page, STUDENT_CODES[0]), 3).flags()
            & Qt.ItemFlag.ItemIsEditable
        )

        with db.transaction() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """SELECT COUNT(*) FROM dbo.SCORES sc
                   INNER JOIN dbo.STUDENT_ENROLLMENTS e
                       ON e.enrollment_id = sc.enrollment_id
                   INNER JOIN dbo.STUDENTS s ON s.student_id = e.student_id
                   WHERE s.student_code LIKE ?""",
                "E10_%",
            )
            score_count_before_navigation = cursor.fetchone()[0]

        teacher_context = AppContext(
            db=db,
            auth_service=object(),
            permission_service=PermissionService(),
            session=UserSession(
                teacher.user_id, TEACHER, "Giáo viên E2E", UserRole.TEACHER
            ),
            academic_service=academic_service,
            enrollment_service=enrollment_service,
            score_service=score_service,
        )
        teacher_window = MainWindow(teacher_context)
        teacher_window.navigate_to("scores")
        assert teacher_window.can_navigate_to("scores") is True

        class DenyScoresPermission(PermissionService):
            @staticmethod
            def can_manage_scores(_session):
                return False

        denied_context = AppContext(
            db=db,
            auth_service=object(),
            permission_service=DenyScoresPermission(),
            session=UserSession(999, "denied", "Denied", UserRole.TEACHER),
            academic_service=academic_service,
            enrollment_service=enrollment_service,
            score_service=score_service,
        )
        denied_window = MainWindow(denied_context)
        with pytest.raises(PermissionError):
            denied_window.navigate_to("scores")

        with db.transaction() as connection:
            cursor = connection.cursor()
            cursor.execute(
                """SELECT COUNT(*) FROM dbo.SCORES sc
                   INNER JOIN dbo.STUDENT_ENROLLMENTS e
                       ON e.enrollment_id = sc.enrollment_id
                   INNER JOIN dbo.STUDENTS s ON s.student_id = e.student_id
                   WHERE s.student_code LIKE ?""",
                "E10_%",
            )
            assert cursor.fetchone()[0] == score_count_before_navigation
    finally:
        cleanup(db)
