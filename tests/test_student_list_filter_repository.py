from models.dto.student_filter import StudentFilter
from models.enums import StudentStatus
from repositories.student_list_repository import StudentListRepository

def test_repository_parameterizes_search_and_filters():
    class Cursor:
        def execute(self,sql,*params): self.sql=sql; self.params=params; return self
        def fetchall(self): return []
    class Conn:
        def __init__(self): self.c=Cursor()
        def cursor(self): return self.c
    c=Conn()
    StudentListRepository().list_students(c,StudentFilter("An",2,3,4,StudentStatus.ACTIVE))
    assert "LIKE ?" in c.c.sql
    assert "current_class.school_year_id = ?" in c.c.sql
    assert "current_class.grade_id = ?" in c.c.sql
    assert "current_class.class_id = ?" in c.c.sql
    assert "%An%" in c.c.params
    assert "An" not in c.c.sql
