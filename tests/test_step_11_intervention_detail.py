from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
import inspect
import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from exceptions import ValidationError
from models.dto import InterventionDetail, InterventionReviewItem
from models.dto.report_dto import SupportReportRow
from models.enums import InterventionStatus, ReviewResult
from repositories.intervention_repository import InterventionRepository
from services.support_service import SupportService
from ui.dialogs.intervention_detail_dialog import (
    InterventionDetailDialog,
)
from ui.pages.support_page import SupportPage
from tests.test_report_repository_integration import (
    cleanup,
    get_test_db,
    seed_report_data,
)


def app():
    return QApplication.instance() or QApplication([])


def review(
    review_id=1,
    review_date=date(2026, 11, 1),
    score=Decimal("3.20"),
    result=ReviewResult.NOT_PASSED,
    notes="Review 1",
):
    return InterventionReviewItem(
        review_id=review_id,
        intervention_id=101,
        score_id=200 + review_id,
        review_date=review_date,
        result=result,
        notes=notes,
        created_at=datetime(2026, 11, 1, 8, 30),
        score=score,
    )


def detail(reviews=()):
    return InterventionDetail(
        intervention_id=101,
        enrollment_id=201,
        student_id="student-101",
        student_code="HS001",
        full_name="Student A",
        class_name="6A1",
        subject_id=11,
        subject_name="Môn 1",
        trigger_score_id=301,
        trigger_score=Decimal("2.80"),
        responsible_user_id=501,
        responsible_user_name="Teacher A",
        detected_date=date(2026, 10, 10),
        start_date=date(2026, 10, 12),
        status=InterventionStatus.COMPLETED,
        support_method="Học theo nhóm",
        notes="Theo dõi hằng tuần",
        created_at=datetime(2026, 10, 10, 9, 0),
        updated_at=datetime(2026, 11, 20, 10, 15),
        reviews=tuple(reviews),
        grade_number=6,
        school_year_id=2,
        school_year_name="2026-2027",
        subject_code="M1",
        trigger_assessment_name="Giữa kỳ",
    )


class FakeDatabase:
    def __init__(self):
        self.connection = object()
        self.transaction_count = 0

    @contextmanager
    def transaction(self):
        self.transaction_count += 1
        yield self.connection


class DetailRepositoryStub:
    def __init__(self, detail_value=None, reviews=()):
        self.detail_value = detail_value
        self.reviews = list(reviews)
        self.calls = []

    def get_detail(self, connection, intervention_id):
        self.calls.append(("detail", connection, intervention_id))
        return self.detail_value

    def list_reviews(self, connection, intervention_id):
        self.calls.append(("reviews", connection, intervention_id))
        return list(self.reviews)


class DetailServiceStub:
    def __init__(self, value=None):
        self.value = value
        self.calls = []
        self.fail = False

    def get_intervention_detail(self, intervention_id):
        self.calls.append(intervention_id)
        if self.fail:
            raise RuntimeError("raw pyodbc detail")
        return self.value


def test_service_loads_detail_and_reviews_in_one_transaction():
    db = FakeDatabase()
    header = detail()
    reviews = [review(), review(2, date(2026, 11, 20))]
    repository = DetailRepositoryStub(header, reviews)
    service = SupportService(db, intervention_repository=repository)

    result = service.get_intervention_detail(101)

    assert db.transaction_count == 1
    assert result.reviews == tuple(reviews)
    assert repository.calls == [
        ("detail", db.connection, 101),
        ("reviews", db.connection, 101),
    ]


@pytest.mark.parametrize("invalid_id", [0, -1, True, "1", None])
def test_service_rejects_invalid_detail_id_before_transaction(invalid_id):
    db = FakeDatabase()
    repository = DetailRepositoryStub()
    service = SupportService(db, intervention_repository=repository)

    with pytest.raises(ValidationError):
        service.get_intervention_detail(invalid_id)

    assert db.transaction_count == 0
    assert repository.calls == []


def test_service_reports_missing_intervention_without_loading_reviews():
    db = FakeDatabase()
    repository = DetailRepositoryStub(detail_value=None)
    service = SupportService(db, intervention_repository=repository)

    with pytest.raises(ValidationError):
        service.get_intervention_detail(999)

    assert repository.calls == [("detail", db.connection, 999)]


class DetailCursor:
    def __init__(self, row):
        self.row = row
        self.calls = []

    def execute(self, sql, *params):
        self.calls.append((sql, params))
        return self

    def fetchone(self):
        return self.row


class DetailConnection:
    def __init__(self, row):
        self.detail_cursor = DetailCursor(row)

    def cursor(self):
        return self.detail_cursor


def detail_row():
    value = detail()
    return SimpleNamespace(
        **{
            field: getattr(value, field)
            for field in (
                "intervention_id",
                "enrollment_id",
                "student_id",
                "student_code",
                "full_name",
                "class_name",
                "subject_id",
                "subject_name",
                "trigger_score_id",
                "trigger_score",
                "responsible_user_id",
                "responsible_user_name",
                "detected_date",
                "start_date",
                "status",
                "support_method",
                "notes",
                "created_at",
                "updated_at",
                "grade_number",
                "school_year_id",
                "school_year_name",
                "subject_code",
                "trigger_assessment_name",
            )
        }
    )


def test_repository_detail_query_is_parameterized_and_maps_context():
    row = detail_row()
    row.status = row.status.value
    connection = DetailConnection(row)

    result = InterventionRepository().get_detail(connection, 101)

    assert result.student_code == "HS001"
    assert result.grade_number == 6
    assert result.school_year_name == "2026-2027"
    assert result.trigger_assessment_name == "Giữa kỳ"
    assert result.reviews == ()
    assert len(connection.detail_cursor.calls) == 1
    sql, params = connection.detail_cursor.calls[0]
    assert "SELECT *" not in " ".join(sql.upper().split())
    assert params == (101,)


def test_review_mapper_remains_compatible_with_create_output():
    row = SimpleNamespace(
        review_id=1,
        intervention_id=101,
        score_id=201,
        review_date=date(2026, 11, 1),
        result="NOT_PASSED",
        notes=None,
        created_at=datetime(2026, 11, 1),
    )

    mapped = InterventionRepository._map_review(row)

    assert mapped.score is None
    assert mapped.result is ReviewResult.NOT_PASSED


def test_dialog_loads_and_renders_complete_intervention_detail():
    app()
    value = detail([review()])
    service = DetailServiceStub(value)
    dialog = InterventionDetailDialog(101, service)

    assert dialog.load_detail() is value
    assert service.calls == [101]
    assert dialog.student_code_label.text() == "HS001"
    assert dialog.full_name_label.text() == "Student A"
    assert dialog.grade_label.text() == "Khối 6"
    assert dialog.class_label.text() == "6A1"
    assert dialog.school_year_label.text() == "2026-2027"
    assert dialog.subject_label.text() == "Môn 1"
    assert dialog.trigger_assessment_label.text() == "Giữa kỳ"
    assert dialog.trigger_score_label.text() == "2.80"
    assert dialog.detected_date_label.text() == "10/10/2026"
    assert dialog.status_value_label.text() == "Đã đạt ngưỡng"
    assert dialog.start_date_label.text() == "12/10/2026"
    assert dialog.responsible_user_label.text() == "Teacher A"
    assert dialog.support_method_label.text() == "Học theo nhóm"
    assert dialog.notes_label.text() == "Theo dõi hằng tuần"


def test_dialog_without_reviews_renders_review_empty_state():
    app()
    dialog = InterventionDetailDialog(101, DetailServiceStub(detail()))

    dialog.load_detail()

    assert dialog.review_table.rowCount() == 0
    assert dialog.review_table.isHidden()
    assert dialog.review_empty_label.isHidden() is False
    assert dialog.review_empty_label.text() == "Chưa có lịch sử đánh giá."


def test_dialog_renders_all_reviews_in_chronological_order():
    app()
    reviews = (
        review(1, date(2026, 11, 1), Decimal("3.20")),
        review(
            2,
            date(2026, 11, 20),
            Decimal("4.20"),
            ReviewResult.PASSED,
            "Đã đạt",
        ),
    )
    dialog = InterventionDetailDialog(
        101,
        DetailServiceStub(detail(reviews)),
    )

    dialog.load_detail()

    assert dialog.review_table.rowCount() == 2
    assert dialog.review_table.item(0, 0).text() == "01/11/2026"
    assert dialog.review_table.item(0, 1).text() == "3.20"
    assert dialog.review_table.item(0, 2).text() == "Chưa đạt ngưỡng"
    assert dialog.review_table.item(1, 0).text() == "20/11/2026"
    assert dialog.review_table.item(1, 1).text() == "4.20"
    assert dialog.review_table.item(1, 2).text() == "Đạt ngưỡng"
    assert dialog.review_table.item(1, 3).text() == "Đã đạt"


def test_dialog_read_failure_is_normalized_and_remains_closable():
    app()
    service = DetailServiceStub()
    service.fail = True
    dialog = InterventionDetailDialog(999, service)

    assert dialog.load_detail() is None
    assert dialog.detail is None
    assert "raw pyodbc detail" not in dialog.error_label.text()
    assert dialog.error_label.text() == "Không thể tải chi tiết hồ sơ bổ trợ."
    assert dialog.close_buttons.isEnabled()


def report_row(intervention_id=731):
    return SupportReportRow(
        intervention_id=intervention_id,
        student_code="HS001",
        full_name="Student A",
        grade_number=6,
        class_name="6A1",
        subject_code="M1",
        subject_name="Môn 1",
        detected_date=date(2026, 10, 10),
        start_date=None,
        status="DETECTED",
        trigger_score=Decimal("2.80"),
    )


class DialogStub:
    last_kwargs = None
    loaded = False
    executed = False

    def __init__(self, **kwargs):
        DialogStub.last_kwargs = kwargs

    def load_detail(self):
        DialogStub.loaded = True

    def exec(self):
        DialogStub.executed = True
        return 0


def test_support_page_double_click_opens_id_stored_in_row_user_role():
    app()
    service = DetailServiceStub(detail())
    page = SupportPage(
        intervention_detail_service=service,
        detail_dialog_factory=DialogStub,
    )
    emitted = []
    page.intervention_requested.connect(emitted.append)
    page.set_support_cases([report_row(731)])

    page._on_row_activated(0, 9)

    assert emitted == [731]
    assert DialogStub.last_kwargs["intervention_id"] == 731
    assert DialogStub.last_kwargs["intervention_service"] is service
    assert DialogStub.loaded is True
    assert DialogStub.executed is True


def test_detail_ui_has_no_sql_repository_or_transition_calls():
    modules = (
        inspect.getmodule(InterventionDetailDialog),
        inspect.getmodule(SupportPage),
    )
    source = "\n".join(inspect.getsource(module) for module in modules)
    upper_source = source.upper()

    for forbidden in (
        "SELECT ",
        "INSERT ",
        "UPDATE ",
        "DELETE ",
        "REPOSITORY",
        "PLAN_INTERVENTION",
        "START_INTERVENTION",
        "MARK_WAITING_REVIEW",
        "CONTINUE_INTERVENTION",
        "REVIEW_INTERVENTION",
    ):
        assert forbidden not in upper_source


def test_real_detail_reads_all_reviews_in_order_without_state_change():
    test_db = get_test_db()
    cleanup(test_db)

    try:
        seeded = seed_report_data(test_db)
        intervention_id = seeded["completed_intervention_id"]
        repository = InterventionRepository()

        with test_db.transaction() as connection:
            status_before = repository.get_by_id(
                connection,
                intervention_id,
            ).status

        result = SupportService(test_db).get_intervention_detail(
            intervention_id
        )

        assert result.student_code == "TRPT_HS001"
        assert result.grade_number == 10
        assert result.class_name == "TRPT_10A1"
        assert result.school_year_name == "TRPT_2026_2027"
        assert result.subject_code == "TRPT_TOAN"
        assert result.trigger_score == Decimal("2.80")
        assert [item.review_date for item in result.reviews] == [
            date(2026, 11, 1),
            date(2026, 11, 20),
        ]
        assert [item.score for item in result.reviews] == [
            Decimal("3.20"),
            Decimal("4.20"),
        ]
        assert [item.result for item in result.reviews] == [
            ReviewResult.NOT_PASSED,
            ReviewResult.PASSED,
        ]

        with test_db.transaction() as connection:
            status_after = repository.get_by_id(
                connection,
                intervention_id,
            ).status

        assert status_after == status_before
    finally:
        cleanup(test_db)
