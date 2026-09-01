from datetime import date
from models.dto.student_list import StudentListItem
from models.enums import StudentStatus

def test_student_list_item_contains_current_class_read_model():
    item=StudentListItem("id1","HS01","Nguyễn Văn A",date(2012,1,2),"Nam","6A1",6,StudentStatus.ACTIVE)
    assert item.current_class_name=="6A1"
    assert item.current_grade_number==6
