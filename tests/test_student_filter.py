from models.dto.student_filter import StudentFilter
def test_default_filter_means_all_students():
    f=StudentFilter()
    assert f.search_text==""
    assert f.school_year_id is None and f.grade_id is None and f.class_id is None and f.status is None
