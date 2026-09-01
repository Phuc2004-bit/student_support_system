import os
from datetime import date, datetime
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")

from PySide6.QtWidgets import QApplication, QDialog
from models.dto import Student, StudentUpdateData
from models.dto.student_list import StudentListItem
from models.enums import StudentStatus
from ui.pages.students_page import StudentsPage

def app(): return QApplication.instance() or QApplication([])

def list_row():
    return StudentListItem("id1","HS01","A",date(2012,1,1),"Nam","6A1",6,StudentStatus.ACTIVE)

def student():
    now=datetime.now()
    return Student("id1","HS01","A",date(2012,1,1),"Nam",None,None,None,StudentStatus.ACTIVE,now,now)

class ListService:
    def list_students(self,filters=None): return [list_row()]

class Crud:
    def __init__(self): self.got=None; self.updated=None
    def get_student(self,student_id): self.got=student_id; return student()
    def update_student(self,student_id,data): self.updated=(student_id,data); return student()

class Dialog:
    DialogCode=QDialog.DialogCode
    def __init__(self,parent=None,student=None): self.student=student
    def exec(self): return QDialog.DialogCode.Accepted
    def update_data(self): return StudentUpdateData(full_name="B")

def test_edit_selected_student_calls_get_and_update(monkeypatch):
    app(); crud=Crud(); page=StudentsPage(ListService(),student_crud_service=crud,dialog_factory=Dialog)
    page.set_students([list_row()]); page.table.selectRow(0)
    monkeypatch.setattr("ui.pages.students_page.QMessageBox.information",lambda *a,**k: None)
    assert page._edit_selected_student() is True
    assert crud.got=="id1"
    assert crud.updated[0]=="id1"
    assert crud.updated[1].full_name=="B"

def test_edit_button_enabled_only_with_selection():
    app(); page=StudentsPage(ListService())
    page.set_students([list_row()])
    assert page.edit_button.isEnabled() is False
    page.table.selectRow(0)
    assert page.edit_button.isEnabled() is True
