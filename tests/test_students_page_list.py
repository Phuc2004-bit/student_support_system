import os
from datetime import date
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
from PySide6.QtWidgets import QApplication
from models.dto.student_list import StudentListItem
from models.enums import StudentStatus
from ui.pages.students_page import StudentsPage

def app(): return QApplication.instance() or QApplication([])
def item(student_id="id1",class_name="6A1"):
    return StudentListItem(student_id,"HS001","Nguyễn Văn A",date(2012,1,2),"Nam",class_name,6,StudentStatus.ACTIVE)

def test_set_students_renders_rows_and_count():
    app(); page=StudentsPage(); page.set_students((item(),))
    assert page.table.rowCount()==1
    assert page.table.item(0,0).text()=="HS001"
    assert page.table.item(0,2).text()=="02/01/2012"
    assert page.table.item(0,4).text()=="6A1"
    assert page.count_label.text()=="1 học sinh"

def test_missing_class_is_rendered_safely():
    app(); page=StudentsPage(); page.set_students((item(class_name=None),))
    assert page.table.item(0,4).text()=="Chưa xếp lớp"

def test_refresh_uses_list_service():
    app()
    class Service:
        def __init__(self):
            self.calls = 0

        def list_students(self, filters=None):
            self.calls += 1
            return [item()]
    service=Service(); page=StudentsPage(service)
    assert page.refresh_students() is True
    assert service.calls==1
    assert page.table.rowCount()==1

def test_double_click_emits_student_id():
    app(); page=StudentsPage(); page.set_students((item("student-123"),))
    received=[]
    page.student_requested.connect(received.append)
    page._on_row_activated(0,0)
    assert received==["student-123"]
