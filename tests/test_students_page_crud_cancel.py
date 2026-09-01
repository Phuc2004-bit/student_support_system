import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
from PySide6.QtWidgets import QApplication, QDialog
from ui.pages.students_page import StudentsPage

def app(): return QApplication.instance() or QApplication([])

class ListService:
    def list_students(self,filters=None): return []

class Crud:
    def create_student(self,data): raise AssertionError("Không được gọi")

class CancelDialog:
    DialogCode=QDialog.DialogCode
    def __init__(self,parent=None,student=None): pass
    def exec(self): return QDialog.DialogCode.Rejected

def test_cancel_create_does_not_write_database():
    app(); page=StudentsPage(ListService(),student_crud_service=Crud(),dialog_factory=CancelDialog)
    assert page._create_student() is False

def test_add_button_still_emits_public_signal():
    app(); page=StudentsPage(ListService())
    calls=[]
    page.add_student_requested.connect(lambda:calls.append(True))
    page.add_button.click()
    assert calls==[True]
