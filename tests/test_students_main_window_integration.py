import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app_context import AppContext
from models.dto import UserSession
from models.enums import UserRole
from services.permission_service import PermissionService
from ui.main_window import MainWindow
from ui.pages.students_page import StudentsPage


def app():
    return QApplication.instance() or QApplication([])


class StudentListService:
    def __init__(self):
        self.calls = 0

    def list_students(self, filters=None):
        self.calls += 1
        return []


class StudentService:
    pass


class EnrollmentService:
    pass


class StudentProfileService:
    pass


def make_context(role: UserRole):
    return AppContext(
        db=object(),
        auth_service=object(),
        permission_service=PermissionService(),
        session=UserSession(1, "user", "Người dùng", role),
        student_list_service=StudentListService(),
        student_service=StudentService(),
        enrollment_service=EnrollmentService(),
        student_profile_service=StudentProfileService(),
    )


def test_main_window_registers_real_students_page_with_services():
    app()
    context = make_context(UserRole.ADMIN)
    window = MainWindow(context)

    page = window.pages["students"]

    assert isinstance(page, StudentsPage)
    assert page.student_service is context.student_list_service
    assert page.student_crud_service is context.student_service
    assert page.enrollment_service is context.enrollment_service
    assert page.student_profile_service is context.student_profile_service

    window.navigate_to("students")

    assert context.student_list_service.calls == 1


def test_teacher_can_navigate_to_real_students_page():
    app()
    window = MainWindow(make_context(UserRole.TEACHER))

    window.navigate_to("students")

    assert isinstance(window.pages["students"], StudentsPage)
    assert window.page_stack.current_key == "students"
