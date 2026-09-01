import os
from datetime import date
from decimal import Decimal

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QDialog

from app_context import AppContext
from config.database import db_settings
from database.connection import DatabaseManager
from models.dto import StudentCreateData, StudentUpdateData, UserSession
from models.enums import EnrollmentStatus, InterventionStatus, StudentStatus, UserRole
from repositories import AcademicRepository, InterventionRepository
from services import (
    AcademicService,
    EnrollmentService,
    ScoreService,
    StudentProfileService,
    StudentService,
)
from services.permission_service import PermissionService
from services.student_list_service import StudentListService
from ui.dialogs.enrollment_dialog import EnrollmentDialog
from ui.dialogs.student_profile_dialog import StudentProfileDialog
from ui.main_window import MainWindow


CODE = "S9_001"
YEAR = "S9_2627"
CLASS_1 = "S9A1"
CLASS_2 = "S9A2"
SUBJECT = "S9_TOAN"
ASSESSMENT = "S9_GK"


def app():
    return QApplication.instance() or QApplication([])


def get_test_db() -> DatabaseManager:
    connection_string = db_settings.connection_string().replace(
        "DATABASE=student_support_db;",
        "DATABASE=student_support_db_test;",
    )
    return DatabaseManager(connection_string)


def cleanup(db: DatabaseManager) -> None:
    with db.transaction() as connection:
        cursor = connection.cursor()
        cursor.execute(
            """
            DELETE FROM dbo.INTERVENTION_REVIEWS WHERE intervention_id IN (
                SELECT i.intervention_id FROM dbo.INTERVENTIONS i
                INNER JOIN dbo.STUDENT_ENROLLMENTS e ON e.enrollment_id = i.enrollment_id
                INNER JOIN dbo.STUDENTS s ON s.student_id = e.student_id
                WHERE s.student_code = ?
            )
            """, CODE
        )
        cursor.execute(
            """
            DELETE FROM dbo.INTERVENTIONS WHERE enrollment_id IN (
                SELECT e.enrollment_id FROM dbo.STUDENT_ENROLLMENTS e
                INNER JOIN dbo.STUDENTS s ON s.student_id = e.student_id
                WHERE s.student_code = ?
            )
            """, CODE
        )
        cursor.execute(
            """
            DELETE FROM dbo.SCORES WHERE enrollment_id IN (
                SELECT e.enrollment_id FROM dbo.STUDENT_ENROLLMENTS e
                INNER JOIN dbo.STUDENTS s ON s.student_id = e.student_id
                WHERE s.student_code = ?
            )
            """, CODE
        )
        cursor.execute(
            """
            DELETE FROM dbo.STUDENT_ENROLLMENTS WHERE student_id IN (
                SELECT student_id FROM dbo.STUDENTS WHERE student_code = ?
            )
            """, CODE
        )
        cursor.execute("DELETE FROM dbo.STUDENTS WHERE student_code = ?", CODE)
        cursor.execute("DELETE FROM dbo.ASSESSMENTS WHERE assessment_name = ?", ASSESSMENT)
        cursor.execute("DELETE FROM dbo.CLASSES WHERE class_name IN (?, ?)", CLASS_1, CLASS_2)
        cursor.execute("DELETE FROM dbo.SUBJECTS WHERE subject_code = ?", SUBJECT)
        cursor.execute("DELETE FROM dbo.SCHOOL_YEARS WHERE year_name = ?", YEAR)


class StudentDialog:
    DialogCode = QDialog.DialogCode

    def __init__(self, student=None, parent=None):
        self.student = student

    def exec(self):
        return QDialog.DialogCode.Accepted

    def create_data(self):
        return StudentCreateData(CODE, "Student Nine")

    def update_data(self):
        return StudentUpdateData("Student Nine Edited")


class EnrollmentDialogStub:
    DialogCode = QDialog.DialogCode

    def __init__(self, mode, current_class_id=None, **_kwargs):
        self.mode = mode
        self.current_class_id = current_class_id

    def load_options(self):
        pass

    def exec(self):
        return QDialog.DialogCode.Accepted

    def selected_class_id(self):
        return class_1_id if self.mode == EnrollmentDialog.MODE_ASSIGN else class_2_id

    def action_date(self):
        return date(2026, 9, 1) if self.mode == EnrollmentDialog.MODE_ASSIGN else date(2026, 10, 1)


class ProfileDialogStub:
    profile = None
    student_id = None

    def __init__(self, student_id, profile_service, parent=None):
        self.student_id = student_id
        self.profile_service = profile_service

    def load_profile(self):
        ProfileDialogStub.student_id = self.student_id
        ProfileDialogStub.profile = self.profile_service.get_profile(self.student_id)

    def exec(self):
        return 0


class_1_id = 0
class_2_id = 0


def test_students_enrollment_and_profile_end_to_end(monkeypatch):
    global class_1_id, class_2_id
    app()
    db = get_test_db()
    academic_repository = AcademicRepository()
    intervention_repository = InterventionRepository()
    academic_service = AcademicService(db)
    student_service = StudentService(db)
    enrollment_service = EnrollmentService(db)
    score_service = ScoreService(db)
    profile_service = StudentProfileService(db)

    cleanup(db)
    try:
        with db.transaction() as connection:
            cursor = connection.cursor()
            cursor.execute("SELECT grade_id FROM dbo.GRADES WHERE grade_number = ?", 10)
            row = cursor.fetchone()
            if row is None:
                cursor.execute(
                    "INSERT INTO dbo.GRADES (grade_number, grade_name) OUTPUT INSERTED.grade_id VALUES (?, ?)",
                    10, "Khối 10",
                )
                grade_id = cursor.fetchone()[0]
            else:
                grade_id = row[0]
            year_id = academic_repository.create_school_year(
                connection, YEAR, date(2026, 9, 1), date(2027, 5, 31)
            )
            class_1_id = academic_repository.create_class(connection, CLASS_1, grade_id, year_id)
            class_2_id = academic_repository.create_class(connection, CLASS_2, grade_id, year_id)
            subject_id = academic_repository.create_subject(connection, SUBJECT, "Toán S9")
            assessment = academic_repository.create_assessment(
                connection, subject_id, year_id, ASSESSMENT, 1, "MIDTERM", date(2026, 9, 15)
            )

        context = AppContext(
            db=db,
            auth_service=object(),
            permission_service=PermissionService(),
            session=UserSession(1, "admin", "Admin", UserRole.ADMIN),
            academic_service=academic_service,
            student_list_service=StudentListService(db),
            student_service=student_service,
            enrollment_service=enrollment_service,
            student_profile_service=profile_service,
        )
        monkeypatch.setattr("ui.pages.students_page.QMessageBox.information", lambda *_args, **_kwargs: None)
        window = MainWindow(context)
        page = window.pages["students"]
        page.dialog_factory = StudentDialog
        page.enrollment_dialog_factory = EnrollmentDialogStub
        page.profile_dialog_factory = ProfileDialogStub

        window.navigate_to("students")
        page.filter_widget.search_input.setText(CODE)
        page.filter_widget._timer.stop()
        page.filter_widget._emit()
        assert page.table.rowCount() == 0
        assert page._create_student() is True
        assert page.table.rowCount() == 1

        assert page.table.item(0, 0).text() == CODE
        assert page.last_filter.search_text == CODE

        page.table.selectRow(0)
        assert page._edit_selected_student() is True
        assert page.table.item(0, 1).text() == "Student Nine Edited"

        assert page._assign_selected_student() is True
        history = enrollment_service.get_student_history(page.selected_student_id())
        assert len(history) == 1
        assert history[0].status == EnrollmentStatus.ACTIVE
        assert page.current_enrollment.class_id == class_1_id

        assert page._transfer_selected_student() is True
        history = enrollment_service.get_student_history(page.selected_student_id())
        assert [item.class_id for item in history] == [class_1_id, class_2_id]
        assert [item.status for item in history] == [
            EnrollmentStatus.TRANSFERRED,
            EnrollmentStatus.ACTIVE,
        ]
        assert page.enrollment_history_widget.table.rowCount() == 2
        assert page.current_enrollment.class_id == class_2_id

        active = [item for item in history if item.status == EnrollmentStatus.ACTIVE]
        assert len(active) == 1

        page.filter_widget.school_year_combo.setCurrentIndex(
            page.filter_widget.school_year_combo.findData(year_id)
        )
        page.filter_widget.grade_combo.setCurrentIndex(
            page.filter_widget.grade_combo.findData(grade_id)
        )
        page.filter_widget.class_combo.setCurrentIndex(
            page.filter_widget.class_combo.findData(class_2_id)
        )
        page.filter_widget.status_combo.setCurrentIndex(
            page.filter_widget.status_combo.findData(StudentStatus.ACTIVE)
        )
        assert page.table.rowCount() == 1
        assert page.last_filter.school_year_id == year_id
        assert page.last_filter.grade_id == grade_id
        assert page.last_filter.class_id == class_2_id
        assert page.last_filter.status == StudentStatus.ACTIVE

        score = score_service.create_score(active[0].enrollment_id, assessment.assessment_id, Decimal("3.00"))
        with db.transaction() as connection:
            intervention_repository.create(
                connection, active[0].enrollment_id, subject_id, score.score_id, date(2026, 10, 2)
            )

        page.table.selectRow(0)
        page._on_row_activated(0, 0)
        assert ProfileDialogStub.student_id == page.selected_student_id()
        assert ProfileDialogStub.profile.student.full_name == "Student Nine Edited"
        assert len(ProfileDialogStub.profile.enrollment_history) == 2
        assert ProfileDialogStub.profile.score_history[0].score == Decimal("3.00")
        assert ProfileDialogStub.profile.intervention_history[0].status == InterventionStatus.DETECTED

        dialog = StudentProfileDialog(page.selected_student_id(), profile_service)
        dialog.load_profile()
        assert dialog.tabs.count() == 4
        assert dialog.enrollment_history_widget.table.rowCount() == 2
        assert dialog.score_table.rowCount() == 1
        assert dialog.intervention_table.rowCount() == 1
    finally:
        cleanup(db)
