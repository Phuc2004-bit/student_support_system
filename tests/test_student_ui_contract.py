from services.student_contract import StudentServiceContract

def test_student_service_contract_declares_required_ui_methods():
    names=StudentServiceContract.__dict__
    assert "list_students" in names
    assert "get_student" in names

def test_student_contract_does_not_expose_repository_or_database():
    names=set(StudentServiceContract.__dict__)
    assert "repository" not in names
    assert "db" not in names
