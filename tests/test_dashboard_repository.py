from repositories.dashboard_repository import DashboardRepository


def test_build_filter_sql_with_only_school_year():
    sql, params = DashboardRepository._build_filter_sql(
        school_year_id=1,
        grade_id=None,
        class_id=None,
        subject_id=None,
    )

    assert sql == "WHERE c.school_year_id = ?"
    assert params == [1]


def test_build_filter_sql_with_all_filters():
    sql, params = DashboardRepository._build_filter_sql(
        school_year_id=1,
        grade_id=2,
        class_id=3,
        subject_id=4,
    )

    assert "c.school_year_id = ?" in sql
    assert "c.grade_id = ?" in sql
    assert "c.class_id = ?" in sql
    assert "i.subject_id = ?" in sql
    assert params == [1, 2, 3, 4]


def test_dashboard_repository_open_statuses_exclude_completed():
    statuses = DashboardRepository.OPEN_STATUSES

    assert "DETECTED" in statuses
    assert "PLANNED" in statuses
    assert "IN_PROGRESS" in statuses
    assert "WAITING_REVIEW" in statuses
    assert "CONTINUE" in statuses
    assert "COMPLETED" not in statuses
