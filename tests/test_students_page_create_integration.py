import os
from datetime import date
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")

from PySide6.QtWidgets import QApplication, QDialog
from models.dto import StudentCreateData
from models.dto.student_list import StudentListItem
from models.enums import StudentStatus
from ui.pages.students_page import StudentsPage

def app():
    return QApplication.instance() or QApplication([])

def row():
    return StudentListItem("id1","HS01","A",date(2012,1,1),"Nam",None,None,StudentStatus.ACTIVE)

class ListService:
    def __init__(self): self.calls=0
    def list_students(self,filters=None): self.calls+=1; return [row()]

class Created:
    student_id="new-id"

class Crud:
    def __init__(self): self.data=None
    def create_student(self,data): self.data=data; return Created()

class Dialog:
    DialogCode=QDialog.DialogCode
    def __init__(self,parent=None,student=None): pass
    def exec(self): return QDialog.DialogCode.Accepted
    def create_data(self): return StudentCreateData(student_code="HS99",full_name="Lan")

def test_create_student_calls_service_and_refreshes(monkeypatch):
    app(); listing=ListService(); crud=Crud()
    page=StudentsPage(listing,student_crud_service=crud,dialog_factory=Dialog)
    monkeypatch.setattr("ui.pages.students_page.QMessageBox.information",lambda *a,**k: None)
    saved=[]; page.student_saved.connect(saved.append)
    assert page._create_student() is True
    assert crud.data.student_code=="HS99"
    assert listing.calls==1
    assert saved==["new-id"]

def test_create_without_crud_service_returns_false():
    app(); page=StudentsPage(ListService())
    assert page._create_student() is False
