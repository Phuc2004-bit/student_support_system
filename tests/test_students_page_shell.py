import os
os.environ.setdefault("QT_QPA_PLATFORM","offscreen")
from PySide6.QtWidgets import QApplication
from ui.pages.students_page import StudentsPage

def get_app():
    return QApplication.instance() or QApplication([])

def test_students_page_builds_expected_shell():
    get_app(); page=StudentsPage()
    assert page.objectName()=="studentsPage"
    assert page.title_label.text()=="Học sinh"
    assert page.table.columnCount()==6
    assert page.table.rowCount()==0

def test_students_page_has_search_and_primary_actions():
    get_app(); page=StudentsPage()
    assert "mã học sinh" in page.search_input.placeholderText().lower()
    assert page.add_button.text()=="+ Thêm học sinh"
    assert page.refresh_button.text()=="Làm mới"

def test_students_page_formats_student_count():
    get_app(); page=StudentsPage(); page.set_student_count(1000)
    assert page.count_label.text()=="1.000 học sinh"

def test_students_page_rejects_negative_count():
    get_app(); page=StudentsPage()
    try: page.set_student_count(-1)
    except ValueError: pass
    else: raise AssertionError("Phải từ chối số lượng âm.")

def test_students_page_action_signals_are_emitted():
    get_app(); page=StudentsPage(); calls={"add":0,"refresh":0}
    page.add_student_requested.connect(lambda:calls.__setitem__("add",calls["add"]+1))
    page.refresh_requested.connect(lambda:calls.__setitem__("refresh",calls["refresh"]+1))
    page.add_button.click(); page.refresh_button.click()
    assert calls=={"add":1,"refresh":1}
