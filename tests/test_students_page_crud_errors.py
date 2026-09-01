import os
from datetime import date
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")

from PySide6.QtWidgets import QApplication, QDialog
from exceptions import DuplicateError
from models.dto import StudentCreateData
from models.dto.student_list import StudentListItem
from models.enums import StudentStatus
from ui.pages.students_page import StudentsPage

def app(): return QApplication.instance() or QApplication([])

class ListService:
    def list_students(self,filters=None): return []

class FailingCrud:
    def create_student(self,data): raise DuplicateError("Mã học sinh đã tồn tại.")

class Dialog:
    DialogCode=QDialog.DialogCode
    def __init__(self,parent=None,student=None): pass
    def exec(self): return QDialog.DialogCode.Accepted
    def create_data(self): return StudentCreateData(student_code="HS01",full_name="A")

def test_create_error_is_shown_and_page_does_not_crash(monkeypatch):
    app(); page=StudentsPage(ListService(),student_crud_service=FailingCrud(),dialog_factory=Dialog)
    shown=[]
    monkeypatch.setattr("ui.pages.students_page.QMessageBox.warning",lambda *args,**kwargs: shown.append(args))
    assert page._create_student() is False
    assert "Mã học sinh đã tồn tại." in shown[0][2]

def test_error_message_has_safe_fallback():
    assert StudentsPage._error_message(Exception(""))=="Đã xảy ra lỗi không xác định."
