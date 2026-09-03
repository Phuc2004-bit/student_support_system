from contextlib import contextmanager
from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal
import inspect
import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QDate
from PySide6.QtWidgets import QApplication, QDialog

from exceptions import (
    BusinessRuleError,
    DuplicateError,
    InvalidStateTransitionError,
    MissingSupportRuleError,
    ValidationError,
)
from models.dto import Assessment, Intervention, Score, StudentCreateData
from models.enums import (
    AssessmentStatus,
    InterventionStatus,
    ReviewResult,
    UserRole,
)
from repositories import (
    AcademicRepository,
    InterventionRepository,
    ScoreRepository,
    SupportRuleRepository,
    UserRepository,
)
from services import EnrollmentService, ScoreService, StudentService
from services.support_service import SupportService
from ui.dialogs.intervention_detail_dialog import InterventionDetailDialog
from ui.dialogs.intervention_review_dialog import InterventionReviewDialog
from ui.pages.support_page import SupportPage
from tests.test_step_11_intervention_detail import detail, report_row
from tests.test_support_service_review_integration import (
    TEST_CODE,
    TEST_YEAR,
    cleanup,
    get_test_db,
)


NOW = datetime(2026, 11, 1, 8, 0)


def app():
    return QApplication.instance() or QApplication([])


def assessment(
    assessment_id=402,
    subject_id=11,
    school_year_id=2,
    name="Đánh giá lại",
):
    return Assessment(
        assessment_id,
        subject_id,
        school_year_id,
        name,
        1,
        "REVIEW",
        date(2026, 11, 1),
        AssessmentStatus.ACTIVE,
        NOW,
    )


class AssessmentServiceStub:
    def __init__(self, values=()):
        self.values = list(values)
        self.calls = []

    def list_assessments(self, **filters):
        self.calls.append(filters)
        return list(self.values)


class ReviewServiceStub:
    def __init__(self, status=InterventionStatus.COMPLETED):
        self.calls = []
        self.fail = False
        self.status = status

    def review_intervention(self, **data):
        self.calls.append(data)
        if self.fail:
            raise RuntimeError("raw database error")
        return SimpleNamespace(
            intervention_id=data["intervention_id"],
            status=self.status,
        )


@pytest.mark.parametrize(
    ("status", "visible"),
    [
        (InterventionStatus.DETECTED, False),
        (InterventionStatus.PLANNED, False),
        (InterventionStatus.IN_PROGRESS, False),
        (InterventionStatus.WAITING_REVIEW, True),
        (InterventionStatus.CONTINUE, False),
        (InterventionStatus.COMPLETED, False),
    ],
)
def test_review_action_is_available_only_for_waiting_review(status, visible):
    app()
    value = replace(detail(), status=status)
    dialog = InterventionDetailDialog(
        101,
        SimpleNamespace(get_intervention_detail=lambda _id: value),
        review_service=ReviewServiceStub(),
        assessment_service=AssessmentServiceStub([assessment()]),
    )

    dialog.load_detail()

    assert dialog.review_button.text() == "Đánh giá"
    assert dialog.review_button.isHidden() is (not visible)
    assert dialog.review_button.isEnabled() is visible
    assert not hasattr(dialog, "complete_button")


def test_review_dialog_loads_case_and_matching_active_assessments():
    app()
    value = replace(detail(), status=InterventionStatus.WAITING_REVIEW)
    academic = AssessmentServiceStub([assessment()])
    dialog = InterventionReviewDialog(
        value,
        ReviewServiceStub(),
        academic,
    )

    assert dialog.student_label.text() == "HS001 — Student A"
    assert dialog.context_label.text() == "6A1 — Môn 1"
    assert dialog.trigger_score_label.text() == "2.80"
    assert dialog.status_label.text() == "Chờ đánh giá"
    assert dialog.load_assessments() is True
    assert academic.calls == [{
        "school_year_id": 2,
        "subject_id": 11,
        "status": AssessmentStatus.ACTIVE,
    }]
    assert dialog.assessment_combo.itemData(1) == 402


def test_review_dialog_saves_exact_service_input():
    app()
    value = replace(detail(), status=InterventionStatus.WAITING_REVIEW)
    service = ReviewServiceStub()
    dialog = InterventionReviewDialog(
        value,
        service,
        AssessmentServiceStub([assessment()]),
    )
    dialog.load_assessments()
    dialog.assessment_combo.setCurrentIndex(1)
    dialog.score_input.setText(" 4.00 ")
    dialog.review_date_input.setDate(QDate(2026, 11, 2))
    dialog.notes_input.setPlainText("  Đã tiến bộ  ")

    assert dialog.save_review() is True
    assert service.calls == [{
        "intervention_id": 101,
        "review_date": date(2026, 11, 2),
        "notes": "Đã tiến bộ",
        "assessment_id": 402,
        "score_value": "4.00",
    }]
    assert dialog.result() == QDialog.DialogCode.Accepted


def test_review_dialog_rejects_missing_inputs_before_service():
    app()
    value = replace(detail(), status=InterventionStatus.WAITING_REVIEW)
    service = ReviewServiceStub()
    dialog = InterventionReviewDialog(
        value,
        service,
        AssessmentServiceStub([assessment()]),
    )

    assert dialog.save_review() is False
    dialog.load_assessments()
    dialog.assessment_combo.setCurrentIndex(1)
    assert dialog.save_review() is False
    assert service.calls == []


def test_review_dialog_failure_is_normalized_and_keeps_input():
    app()
    value = replace(detail(), status=InterventionStatus.WAITING_REVIEW)
    service = ReviewServiceStub()
    service.fail = True
    dialog = InterventionReviewDialog(
        value,
        service,
        AssessmentServiceStub([assessment()]),
    )
    dialog.load_assessments()
    dialog.assessment_combo.setCurrentIndex(1)
    dialog.score_input.setText("3.20")

    assert dialog.save_review() is False
    assert "raw database error" not in dialog.error_label.text()
    assert dialog.score_input.text() == "3.20"
    assert dialog.result() != QDialog.DialogCode.Accepted


class AcceptedReviewDialog:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def load_assessments(self):
        return True

    def exec(self):
        return QDialog.DialogCode.Accepted


def test_successful_review_refreshes_detail_and_history():
    app()
    waiting = replace(detail(), status=InterventionStatus.WAITING_REVIEW)
    review = SimpleNamespace(
        review_date=date(2026, 11, 2),
        score=Decimal("4.00"),
        result=ReviewResult.PASSED,
        notes="Đã tiến bộ",
    )
    completed = replace(
        waiting,
        status=InterventionStatus.COMPLETED,
        reviews=(review,),
    )

    class Reader:
        def __init__(self):
            self.values = [waiting, completed]
            self.calls = []

        def get_intervention_detail(self, intervention_id):
            self.calls.append(intervention_id)
            return self.values.pop(0)

    reader = Reader()
    dialog = InterventionDetailDialog(
        101,
        reader,
        review_service=ReviewServiceStub(),
        assessment_service=AssessmentServiceStub([assessment()]),
        review_dialog_factory=AcceptedReviewDialog,
    )
    emitted = []
    dialog.intervention_reviewed.connect(emitted.append)
    dialog.load_detail()

    assert dialog.open_review_dialog() is True
    assert reader.calls == [101, 101]
    assert dialog.detail.status is InterventionStatus.COMPLETED
    assert dialog.review_table.rowCount() == 1
    assert dialog.review_table.item(0, 1).text() == "4.00"
    assert dialog.review_table.item(0, 2).text() == "Đạt ngưỡng"
    assert dialog.review_button.isHidden()
    assert emitted == [101]


class SimpleSignal:
    def __init__(self):
        self.callback = None

    def connect(self, callback):
        self.callback = callback

    def emit(self, value):
        self.callback(value)


class DetailDialogThatReviews:
    def __init__(self, **_kwargs):
        self.intervention_reviewed = SimpleSignal()

    def load_detail(self):
        return None

    def exec(self):
        self.intervention_reviewed.emit(731)
        return 0


@pytest.mark.parametrize(
    ("filter_status", "result_status", "expected_rows"),
    [
        (InterventionStatus.WAITING_REVIEW, "COMPLETED", 0),
        (InterventionStatus.COMPLETED, "COMPLETED", 1),
        (InterventionStatus.CONTINUE, "CONTINUE", 1),
        (None, "COMPLETED", 1),
    ],
)
def test_support_page_refreshes_matching_filter_after_review(
    filter_status,
    result_status,
    expected_rows,
):
    app()

    class Reader:
        def get_support_cases(self, status=None, **_filters):
            if status == InterventionStatus.WAITING_REVIEW:
                return []
            row = replace(report_row(731), status=result_status)
            status_value = getattr(status, "value", status)
            if status_value is not None and status_value != result_status:
                return []
            return [row]

    page = SupportPage(
        support_read_service=Reader(),
        intervention_detail_service=SimpleNamespace(),
        intervention_review_service=ReviewServiceStub(),
        assessment_service=AssessmentServiceStub(),
        detail_dialog_factory=DetailDialogThatReviews,
    )
    page.school_year_combo.addItem("2026-2027", 2)
    page.school_year_combo.setCurrentIndex(1)
    if filter_status is not None:
        page.status_combo.addItem("filter", filter_status)
        page.status_combo.setCurrentIndex(
            page.status_combo.findData(filter_status)
        )

    assert page.open_intervention_detail(731) is True
    assert page.table.rowCount() == expected_rows


class FakeDatabase:
    def __init__(self):
        self.connection = object()
        self.transactions = 0
        self.commits = 0
        self.rollbacks = 0

    @contextmanager
    def transaction(self):
        self.transactions += 1
        try:
            yield self.connection
        except Exception:
            self.rollbacks += 1
            raise
        else:
            self.commits += 1


@pytest.mark.parametrize(
    "value",
    [
        Decimal("-0.01"),
        Decimal("10.01"),
        "not-a-number",
        True,
        Decimal("NaN"),
        Decimal("Infinity"),
        Decimal("1.234"),
    ],
)
def test_review_score_reuses_score_service_validation(value):
    db = FakeDatabase()
    service = SupportService(db)

    with pytest.raises(ValidationError):
        service.review_intervention(
            101,
            review_date=date(2026, 11, 2),
            assessment_id=402,
            score_value=value,
        )

    assert db.transactions == 0


def stored_intervention(status=InterventionStatus.WAITING_REVIEW):
    return Intervention(
        101,
        201,
        11,
        301,
        501,
        date(2026, 10, 1),
        date(2026, 10, 2),
        status,
        "Học nhóm",
        "Theo dõi",
        NOW,
        NOW,
    )


class ScoreRepositoryStub:
    def __init__(self, existing=None):
        self.existing = existing
        self.created = []
        self.trigger = Score(301, 201, 401, Decimal("2.80"), NOW, NOW)

    def get_by_id(self, _connection, score_id):
        if score_id == 301:
            return self.trigger
        return self.existing

    def get_by_enrollment_assessment(self, *_args):
        return self.existing

    def create(self, _connection, enrollment_id, assessment_id, value):
        score = Score(302, enrollment_id, assessment_id, value, NOW, NOW)
        self.created.append(score)
        return score


class AcademicRepositoryStub:
    def __init__(self, review_assessment=None):
        self.trigger = assessment(401)
        self.review = review_assessment or assessment(402)

    def get_assessment_by_id(self, _connection, assessment_id):
        if assessment_id == 401:
            return self.trigger
        if assessment_id == self.review.assessment_id:
            return self.review
        return None


class RuleRepositoryStub:
    def __init__(self, threshold=Decimal("3.50"), missing=False):
        self.threshold = threshold
        self.missing = missing
        self.calls = []

    def get_active_rule(self, _connection, subject_id, school_year_id):
        self.calls.append((subject_id, school_year_id))
        if self.missing:
            return None
        return SimpleNamespace(threshold=self.threshold)


class InterventionRepositoryStub:
    def __init__(self, status=InterventionStatus.WAITING_REVIEW):
        self.value = stored_intervention(status)
        self.reviews = []
        self.update_calls = []

    def get_by_id(self, _connection, intervention_id):
        return self.value if intervention_id == 101 else None

    def create_review(
        self,
        _connection,
        intervention_id,
        score_id,
        review_date,
        result,
        notes,
    ):
        self.reviews.append(
            (intervention_id, score_id, review_date, result, notes)
        )

    def update_status(self, _connection, intervention_id, status):
        self.update_calls.append((intervention_id, status))
        self.value = replace(self.value, status=status)
        return self.value


def make_review_service(
    *,
    threshold=Decimal("3.50"),
    missing_rule=False,
    review_assessment=None,
    existing_score=None,
    status=InterventionStatus.WAITING_REVIEW,
):
    db = FakeDatabase()
    scores = ScoreRepositoryStub(existing_score)
    academics = AcademicRepositoryStub(review_assessment)
    rules = RuleRepositoryStub(threshold, missing_rule)
    interventions = InterventionRepositoryStub(status)
    service = SupportService(
        db,
        score_repository=scores,
        academic_repository=academics,
        rule_repository=rules,
        intervention_repository=interventions,
    )
    return service, db, scores, rules, interventions


@pytest.mark.parametrize(
    ("score_value", "threshold", "result", "status"),
    [
        ("3.20", Decimal("3.50"), ReviewResult.NOT_PASSED,
         InterventionStatus.CONTINUE),
        ("3.50", Decimal("3.50"), ReviewResult.PASSED,
         InterventionStatus.COMPLETED),
        ("4.00", Decimal("3.50"), ReviewResult.PASSED,
         InterventionStatus.COMPLETED),
        ("4.00", Decimal("4.50"), ReviewResult.NOT_PASSED,
         InterventionStatus.CONTINUE),
    ],
)
def test_review_result_and_status_come_from_active_rule(
    score_value,
    threshold,
    result,
    status,
):
    service, db, scores, rules, interventions = make_review_service(
        threshold=threshold
    )

    reviewed = service.review_intervention(
        101,
        review_date=date(2026, 11, 2),
        notes="Kết quả",
        assessment_id=402,
        score_value=score_value,
    )

    assert reviewed.status is status
    assert scores.created[0].score == Decimal(score_value)
    assert interventions.reviews == [(
        101,
        scores.created[0].score_id,
        date(2026, 11, 2),
        result,
        "Kết quả",
    )]
    assert rules.calls == [(11, 2)]
    assert db.commits == 1


@pytest.mark.parametrize(
    "status",
    [
        InterventionStatus.DETECTED,
        InterventionStatus.PLANNED,
        InterventionStatus.IN_PROGRESS,
        InterventionStatus.CONTINUE,
        InterventionStatus.COMPLETED,
    ],
)
def test_review_service_blocks_every_non_waiting_status(status):
    service, _db, scores, _rules, interventions = make_review_service(
        status=status
    )

    with pytest.raises(InvalidStateTransitionError):
        service.review_intervention(
            101,
            review_date=date(2026, 11, 2),
            assessment_id=402,
            score_value="4.00",
        )

    assert scores.created == []
    assert interventions.reviews == []


def test_wrong_subject_or_school_year_assessment_is_blocked():
    for wrong in (assessment(subject_id=12), assessment(school_year_id=3)):
        service, _db, scores, _rules, interventions = make_review_service(
            review_assessment=wrong
        )
        with pytest.raises(ValidationError):
            service.review_intervention(
                101,
                review_date=date(2026, 11, 2),
                assessment_id=402,
                score_value="4.00",
            )
        assert scores.created == []
        assert interventions.reviews == []


def test_duplicate_score_is_blocked_without_overwrite():
    existing = Score(900, 201, 402, Decimal("6.00"), NOW, NOW)
    service, _db, scores, _rules, interventions = make_review_service(
        existing_score=existing
    )

    with pytest.raises(DuplicateError):
        service.review_intervention(
            101,
            review_date=date(2026, 11, 2),
            assessment_id=402,
            score_value="4.00",
        )

    assert scores.existing.score == Decimal("6.00")
    assert scores.created == []
    assert interventions.reviews == []


def test_missing_rule_rolls_back_before_review_or_transition():
    service, db, scores, _rules, interventions = make_review_service(
        missing_rule=True
    )

    with pytest.raises(MissingSupportRuleError):
        service.review_intervention(
            101,
            review_date=date(2026, 11, 2),
            assessment_id=402,
            score_value="4.00",
        )

    assert scores.created
    assert interventions.reviews == []
    assert interventions.value.status is InterventionStatus.WAITING_REVIEW
    assert db.rollbacks == 1


def test_legacy_wrong_enrollment_score_is_still_blocked():
    wrong_score = Score(900, 999, 402, Decimal("4.00"), NOW, NOW)
    service, _db, _scores, _rules, interventions = make_review_service(
        existing_score=wrong_score
    )

    with pytest.raises(ValidationError):
        service.review_intervention(
            101,
            900,
            date(2026, 11, 2),
        )

    assert interventions.reviews == []


def test_real_atomic_review_creates_locked_score_and_preserves_history():
    db = get_test_db()
    cleanup(db)
    academics = AcademicRepository()
    rules = SupportRuleRepository()
    interventions = InterventionRepository()
    score_repository = ScoreRepository()

    try:
        with db.transaction() as connection:
            cursor = connection.cursor()
            cursor.execute(
                "SELECT grade_id FROM dbo.GRADES WHERE grade_number = ?",
                10,
            )
            row = cursor.fetchone()
            if row is None:
                cursor.execute(
                    "INSERT INTO dbo.GRADES (grade_number, grade_name) "
                    "OUTPUT INSERTED.grade_id VALUES (?, ?)",
                    10,
                    "Khối 10",
                )
                grade_id = cursor.fetchone()[0]
            else:
                grade_id = row[0]
            year_id = academics.create_school_year(
                connection,
                TEST_YEAR,
                date(2026, 9, 7),
                date(2027, 5, 31),
                False,
            )
            class_id = academics.create_class(
                connection, "TRV_10A1", grade_id, year_id
            )
            subject_id = academics.create_subject(
                connection, "TRV_TOAN", "Toán Review Test"
            )
            trigger_assessment = academics.create_assessment(
                connection, subject_id, year_id, "TRV_TRIGGER", 1,
                "MIDTERM", date(2026, 10, 15),
            )
            review_assessment = academics.create_assessment(
                connection, subject_id, year_id, "TRV_REVIEW_1", 1,
                "REVIEW", date(2026, 11, 15),
            )
            rule = rules.create(
                connection, subject_id, year_id, Decimal("4.00")
            )
            teacher = UserRepository().create(
                connection, "trv_teacher", "hash",
                "Giáo viên Review Test", UserRole.TEACHER,
            )

        student = StudentService(db).create_student(
            StudentCreateData(TEST_CODE, "Học sinh Review Test")
        )
        enrollment = EnrollmentService(db).enroll_student(
            student.student_id, class_id, date(2026, 9, 7)
        )
        trigger = ScoreService(db).create_score(
            enrollment.enrollment_id,
            trigger_assessment.assessment_id,
            Decimal("2.80"),
        )
        service = SupportService(db)
        case = service.detect_from_score(trigger.score_id)
        service.plan_intervention(
            case.intervention_id,
            teacher.user_id,
            date(2026, 10, 20),
            "Phụ đạo nhóm nhỏ",
            "Kế hoạch gốc",
        )
        service.start_intervention(case.intervention_id)
        service.mark_waiting_review(case.intervention_id)

        class FailingRepository(InterventionRepository):
            def create_review(self, *args, **kwargs):
                super().create_review(*args, **kwargs)
                raise RuntimeError("forced failure after review")

        with pytest.raises(RuntimeError):
            SupportService(
                db,
                intervention_repository=FailingRepository(),
            ).review_intervention(
                case.intervention_id,
                review_date=date(2026, 11, 15),
                assessment_id=review_assessment.assessment_id,
                score_value="4.00",
            )

        with db.transaction() as connection:
            assert score_repository.get_by_enrollment_assessment(
                connection,
                enrollment.enrollment_id,
                review_assessment.assessment_id,
            ) is None
            assert interventions.list_reviews(
                connection, case.intervention_id
            ) == []
            assert interventions.get_by_id(
                connection, case.intervention_id
            ).status is InterventionStatus.WAITING_REVIEW

        reviewed = service.review_intervention(
            case.intervention_id,
            review_date=date(2026, 11, 15),
            notes="Đạt đúng ngưỡng fixture",
            assessment_id=review_assessment.assessment_id,
            score_value="4.00",
        )
        assert reviewed.status is InterventionStatus.COMPLETED

        with db.transaction() as connection:
            saved_score = score_repository.get_by_enrollment_assessment(
                connection,
                enrollment.enrollment_id,
                review_assessment.assessment_id,
            )
            reviews = interventions.list_reviews(
                connection, case.intervention_id
            )
            saved = interventions.get_by_id(
                connection, case.intervention_id
            )
        assert len(reviews) == 1
        assert reviews[0].score_id == saved_score.score_id
        assert reviews[0].score == Decimal("4.00")
        assert reviews[0].result is ReviewResult.PASSED
        assert reviews[0].review_date == date(2026, 11, 15)
        assert reviews[0].notes == "Đạt đúng ngưỡng fixture"
        assert saved.trigger_score_id == trigger.score_id
        assert saved.responsible_user_id == teacher.user_id
        assert saved.support_method == "Phụ đạo nhóm nhỏ"
        assert saved.notes == "Kế hoạch gốc"
        assert rule.threshold == Decimal("4.00")
        assert ScoreService(db).can_edit_score(saved_score.score_id) is False
        with pytest.raises(BusinessRuleError):
            ScoreService(db).update_score(
                saved_score.score_id,
                Decimal("5.00"),
            )
    finally:
        cleanup(db)


def test_review_ui_contains_no_sql_repository_threshold_or_status_choice():
    modules = (
        inspect.getmodule(InterventionReviewDialog),
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
        "SUPPORT_RULE",
        "THRESHOLD",
        "REVIEWRESULT",
        "CONTINUE_INTERVENTION",
    ):
        assert forbidden not in upper_source
