from models.dto.student_filter import StudentFilter
from services.student_list_service import StudentListService
from exceptions import ValidationError

class Tx:
    def __enter__(self): return object()
    def __exit__(self,*args): return False
class DB:
    def transaction(self): return Tx()
class Repo:
    def __init__(self): self.filters=None
    def list_students(self,c,filters): self.filters=filters; return []

def test_service_forwards_filters():
    repo=Repo(); service=StudentListService(DB(),repo); f=StudentFilter(search_text="Lan",grade_id=6)
    assert service.list_students(f)==[] and repo.filters==f

def test_service_rejects_invalid_filter_id():
    try: StudentListService(DB(),Repo()).list_students(StudentFilter(class_id=0))
    except ValidationError: pass
    else: raise AssertionError("Phải từ chối class_id không hợp lệ")
