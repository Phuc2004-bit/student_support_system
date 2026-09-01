from repositories.student_list_repository import StudentListRepository

def test_repository_uses_single_batch_query_for_current_class():
    class Cursor:
        def __init__(self): self.executions=[]
        def execute(self,sql,*params): self.executions.append((sql,params)); return self
        def fetchall(self): return []
    class Connection:
        def __init__(self): self.cursor_obj=Cursor()
        def cursor(self): return self.cursor_obj
    connection=Connection()
    result=StudentListRepository().list_students_with_current_class(connection)
    assert result==[]
    assert len(connection.cursor_obj.executions)==1
    sql=connection.cursor_obj.executions[0][0]
    assert "OUTER APPLY" in sql
    assert "STUDENT_ENROLLMENTS" in sql
    assert "TOP (1)" in sql
