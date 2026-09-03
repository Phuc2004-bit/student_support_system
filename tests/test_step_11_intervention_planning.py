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

from exceptions import InvalidStateTransitionError
from models.dto import Intervention, User
from models.enums import InterventionStatus, UserRole
from repositories import (
    InterventionRepository,
    ScoreRepository,
    UserRepository,
)
from services.report_service import ReportService
from services.support_service import SupportService
from services.user_service import UserService
from ui.dialogs.intervention_detail_dialog import (
    InterventionDetailDialog,
)
from ui.dialogs.intervention_plan_dialog import InterventionPlanDialog
from ui.pages.support_page import SupportPage
from tests.test_report_repository_integration import (
    cleanup,
    get_test_db,
    seed_report_data,
)
from tests.test_step_11_intervention_detail import detail, report_row


TEST_USERNAME = "s114_teacher"


def app():
    return QApplication.instance() or QApplication([])


def user(user_id=501, role=UserRole.TEACHER, is_active=True):
    return User(
        user_id=user_id,
        username=f"teacher{user_id}",
        password_hash="hash",
        full_name=f"Teacher {user_id}",
        role=role,
        email=None,
        phone=None,
        is_active=is_active,
        created_at=datetime(2026, 9, 1),
        updated_at=datetime(2026, 9, 1),
    )


def intervention(status=InterventionStatus.PLANNED):
    return Intervention(
        intervention_id=101,
        enrollment_id=201,
        subject_id=11,
        trigger_score_id=301,
        responsible_user_id=501,
        detected_date=date(2026, 10, 10),
        start_date=date(2026, 10, 12),
        status=status,
        support_method="Học nhóm",
        notes="Theo dõi",
        created_at=datetime(2026, 10, 10),
        updated_at=datetime(2026, 10, 12),
    )


class UserServiceStub:
    def __init__(self, users=()):
        self.users = list(users)
        self.calls = 0

    def list_active_teachers(self):
        self.calls += 1
        return list(self.users)


class PlanningServiceStub:
    def __init__(self):
        self.calls = []
        self.fail = False

    def plan_intervention(self, **data):
        self.calls.append(data)
        if self.fail:
            raise RuntimeError("raw database error")
        return intervention()


def test_plan_dialog_initializes_with_read_only_student_context():
    app()
    source = detail()
    dialog = InterventionPlanDialog(
        source,
        PlanningServiceStub(),
        UserServiceStub(),
    )

    assert dialog.intervention is source
    assert dialog.student_label.text() == "HS001 — Student A"
    assert dialog.context_label.text() == "6A1 — Môn 1"
    assert dialog.responsible_combo.currentData() is None
    assert dialog.support_method_input.text() == ""
    assert dialog.notes_input.toPlainText() == ""


def test_plan_dialog_loads_responsible_users_from_service():
    app()
    users = [user(501), user(502)]
    service = UserServiceStub(users)
    dialog = InterventionPlanDialog(
        detail(),
        PlanningServiceStub(),
        service,
    )

    assert dialog.load_responsible_users() is True
    assert service.calls == 1
    assert dialog.responsible_combo.count() == 3
    assert dialog.responsible_combo.itemData(1) == 501
    assert dialog.responsible_combo.itemText(2) == "Teacher 502"


def test_plan_dialog_saves_trimmed_data_through_production_contract():
    app()
    planning = PlanningServiceStub()
    dialog = InterventionPlanDialog(
        detail(),
        planning,
        UserServiceStub([user()]),
    )
    dialog.load_responsible_users()
    dialog.responsible_combo.setCurrentIndex(1)
    dialog.start_date_input.setDate(QDate(2026, 10, 12))
    dialog.support_method_input.setText("  Học theo nhóm  ")
    dialog.notes_input.setPlainText("  Theo dõi hằng tuần  ")

    assert dialog.save_plan() is True
    assert planning.calls == [{
        "intervention_id": 101,
        "responsible_user_id": 501,
        "start_date": date(2026, 10, 12),
        "support_method": "Học theo nhóm",
        "notes": "Theo dõi hằng tuần",
    }]
    assert dialog.result() == QDialog.DialogCode.Accepted


def test_cancel_does_not_call_planning_service():
    app()
    planning = PlanningServiceStub()
    dialog = InterventionPlanDialog(
        detail(),
        planning,
        UserServiceStub([user()]),
    )

    dialog.reject()

    assert planning.calls == []
    assert dialog.result() == QDialog.DialogCode.Rejected


def test_missing_responsible_user_is_blocked_before_service():
    app()
    planning = PlanningServiceStub()
    dialog = InterventionPlanDialog(
        detail(),
        planning,
        UserServiceStub(),
    )

    assert dialog.save_plan() is False
    assert planning.calls == []
    assert dialog.error_label.text() == "Vui lòng chọn người phụ trách."


def test_plan_failure_is_normalized_and_dialog_stays_open():
    app()
    planning = PlanningServiceStub()
    planning.fail = True
    dialog = InterventionPlanDialog(
        detail(),
        planning,
        UserServiceStub([user()]),
    )
    dialog.load_responsible_users()
    dialog.responsible_combo.setCurrentIndex(1)

    assert dialog.save_plan() is False
    assert "raw database error" not in dialog.error_label.text()
    assert dialog.result() != QDialog.DialogCode.Accepted


@pytest.mark.parametrize(
    "status",
    [
        InterventionStatus.PLANNED,
        InterventionStatus.IN_PROGRESS,
        InterventionStatus.WAITING_REVIEW,
        InterventionStatus.CONTINUE,
        InterventionStatus.COMPLETED,
    ],
)
def test_service_blocks_planning_from_every_non_detected_status(status):
    class Database:
        @contextmanager
        def transaction(self):
            yield object()

    class Repository:
        update_calls = 0

        def get_by_id(self, _connection, _intervention_id):
            return intervention(status)

        def update_plan(self, *_args, **_kwargs):
            self.update_calls += 1

    repository = Repository()
    service = SupportService(
        Database(),
        intervention_repository=repository,
    )

    with pytest.raises(InvalidStateTransitionError):
        service.plan_intervention(
            101,
            501,
            date(2026, 10, 12),
            "Học nhóm",
        )

    assert repository.update_calls == 0


@pytest.mark.parametrize(
    ("status", "visible"),
    [
        (InterventionStatus.DETECTED, True),
        (InterventionStatus.PLANNED, False),
        (InterventionStatus.IN_PROGRESS, False),
        (InterventionStatus.WAITING_REVIEW, False),
        (InterventionStatus.CONTINUE, False),
        (InterventionStatus.COMPLETED, False),
    ],
)
def test_plan_action_is_available_only_for_detected(status, visible):
    app()
    value = replace(detail(), status=status)
    dialog = InterventionDetailDialog(
        101,
        SimpleNamespace(get_intervention_detail=lambda _id: value),
        planning_service=PlanningServiceStub(),
        user_service=UserServiceStub([user()]),
    )

    dialog.load_detail()

    assert dialog.plan_button.isHidden() is (not visible)
    assert dialog.plan_button.isEnabled() is visible


class AcceptedPlanDialog:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def load_responsible_users(self):
        return True

    def exec(self):
        return QDialog.DialogCode.Accepted


def test_successful_plan_refreshes_detail_from_service():
    app()
    detected = replace(detail(), status=InterventionStatus.DETECTED)
    planned = replace(
        detected,
        status=InterventionStatus.PLANNED,
        responsible_user_name="Teacher 501",
        support_method="Học nhóm",
        notes="Theo dõi",
    )

    class DetailReader:
        def __init__(self):
            self.values = [detected, planned]
            self.calls = []

        def get_intervention_detail(self, intervention_id):
            self.calls.append(intervention_id)
            return self.values.pop(0)

    reader = DetailReader()
    dialog = InterventionDetailDialog(
        101,
        reader,
        planning_service=PlanningServiceStub(),
        user_service=UserServiceStub([user()]),
        plan_dialog_factory=AcceptedPlanDialog,
    )
    emitted = []
    dialog.intervention_planned.connect(emitted.append)
    dialog.load_detail()

    assert dialog.open_plan_dialog() is True
    assert reader.calls == [101, 101]
    assert dialog.detail.status is InterventionStatus.PLANNED
    assert dialog.status_value_label.text() == "Đã lập kế hoạch"
    assert dialog.responsible_user_label.text() == "Teacher 501"
    assert dialog.support_method_label.text() == "Học nhóm"
    assert dialog.notes_label.text() == "Theo dõi"
    assert emitted == [101]


class SimpleSignal:
    def __init__(self):
        self.callback = None

    def connect(self, callback):
        self.callback = callback

    def emit(self, value):
        self.callback(value)


class DetailDialogThatPlans:
    def __init__(self, **_kwargs):
        self.intervention_planned = SimpleSignal()

    def load_detail(self):
        return None

    def exec(self):
        self.intervention_planned.emit(731)
        return 0


class ListReader:
    def __init__(self):
        self.calls = 0

    def get_support_cases(self, **_filters):
        self.calls += 1
        return [report_row(731)]


def test_support_page_refreshes_when_detail_reports_successful_plan():
    app()
    list_reader = ListReader()
    page = SupportPage(
        support_read_service=list_reader,
        intervention_detail_service=SimpleNamespace(),
        intervention_planning_service=PlanningServiceStub(),
        user_service=UserServiceStub([user()]),
        detail_dialog_factory=DetailDialogThatPlans,
    )
    page.school_year_combo.addItem("2026-2027", 2)
    page.school_year_combo.setCurrentIndex(1)
    list_reader.calls = 0

    assert page.open_intervention_detail(731) is True
    assert list_reader.calls == 1
    assert page.items[0].intervention_id == 731


def test_user_service_reads_active_teachers_in_one_transaction():
    class Database:
        def __init__(self):
            self.connection = object()
            self.calls = 0

        @contextmanager
        def transaction(self):
            self.calls += 1
            yield self.connection

    class Repository:
        def __init__(self):
            self.connection = None

        def list_active_teachers(self, connection):
            self.connection = connection
            return [user()]

    db = Database()
    repository = Repository()

    result = UserService(db, repository).list_active_teachers()

    assert result == [user()]
    assert db.calls == 1
    assert repository.connection is db.connection


def test_active_teacher_repository_query_is_parameterized_read_only():
    class Cursor:
        def __init__(self):
            self.call = None

        def execute(self, sql, *params):
            self.call = (sql, params)

        def fetchall(self):
            return []

    cursor = Cursor()
    connection = SimpleNamespace(cursor=lambda: cursor)

    assert UserRepository().list_active_teachers(connection) == []
    sql, params = cursor.call
    normalized = " ".join(sql.upper().split())
    assert "SELECT *" not in normalized
    assert "WHERE ROLE = ? AND IS_ACTIVE = ?" in normalized
    assert params == ("TEACHER", 1)


def cleanup_plan_data(db):
    cleanup(db)
    with db.transaction() as connection:
        connection.cursor().execute(
            "DELETE FROM dbo.USERS WHERE username = ?",
            TEST_USERNAME,
        )


def test_real_detected_to_planned_is_atomic_and_preserves_history():
    db = get_test_db()
    cleanup_plan_data(db)

    try:
        seeded = seed_report_data(db)
        interventions = InterventionRepository()
        scores = ScoreRepository()
        with db.transaction() as connection:
            teacher = UserRepository().create(
                connection,
                TEST_USERNAME,
                "hash",
                "Teacher Plan Test",
                UserRole.TEACHER,
            )
            detected_id = seeded["detected_intervention_id"]
            before = interventions.get_by_id(connection, detected_id)
            trigger_before = scores.get_by_id(
                connection,
                before.trigger_score_id,
            )
            reviews_before = interventions.list_reviews(
                connection,
                detected_id,
            )
            cursor = connection.cursor()
            cursor.execute(
                """SELECT COUNT(*) FROM dbo.INTERVENTIONS
                   WHERE enrollment_id = ? AND subject_id = ?""",
                before.enrollment_id,
                before.subject_id,
            )
            case_count_before = cursor.fetchone()[0]

        class FailingRepository(InterventionRepository):
            def update_plan(self, *args, **kwargs):
                super().update_plan(*args, **kwargs)
                raise RuntimeError("forced failure after update")

        with pytest.raises(RuntimeError):
            SupportService(
                db,
                intervention_repository=FailingRepository(),
            ).plan_intervention(
                detected_id,
                teacher.user_id,
                date(2026, 10, 15),
                "Học nhóm",
                "Theo dõi",
            )

        with db.transaction() as connection:
            after_failure = interventions.get_by_id(
                connection,
                detected_id,
            )
        assert after_failure.status is InterventionStatus.DETECTED
        assert after_failure.responsible_user_id is None
        assert after_failure.start_date is None
        assert after_failure.support_method is None
        assert after_failure.notes is None

        planned = SupportService(db).plan_intervention(
            detected_id,
            teacher.user_id,
            date(2026, 10, 15),
            "Học nhóm",
            "Theo dõi",
        )
        assert planned.status is InterventionStatus.PLANNED

        with pytest.raises(InvalidStateTransitionError):
            SupportService(db).plan_intervention(
                detected_id,
                teacher.user_id,
                date(2026, 10, 16),
            )

        with db.transaction() as connection:
            saved = interventions.get_by_id(connection, detected_id)
            trigger_after = scores.get_by_id(
                connection,
                saved.trigger_score_id,
            )
            reviews_after = interventions.list_reviews(
                connection,
                detected_id,
            )
            cursor = connection.cursor()
            cursor.execute(
                """SELECT COUNT(*) FROM dbo.INTERVENTIONS
                   WHERE enrollment_id = ? AND subject_id = ?""",
                saved.enrollment_id,
                saved.subject_id,
            )
            case_count_after = cursor.fetchone()[0]

        assert saved.responsible_user_id == teacher.user_id
        assert saved.start_date == date(2026, 10, 15)
        assert saved.support_method == "Học nhóm"
        assert saved.notes == "Theo dõi"
        assert saved.trigger_score_id == before.trigger_score_id
        assert trigger_after == trigger_before
        assert reviews_after == reviews_before == []
        assert case_count_after == case_count_before == 1

        report = ReportService(db)
        detected_rows = report.get_support_cases(
            seeded["school_year_id"],
            status=InterventionStatus.DETECTED,
        )
        all_rows = report.get_support_cases(seeded["school_year_id"])
        assert detected_rows == []
        assert len(all_rows) == 2
        assert next(
            row for row in all_rows
            if row.intervention_id == detected_id
        ).status == "PLANNED"
    finally:
        cleanup_plan_data(db)


def test_planning_ui_has_no_sql_repository_or_later_transition_calls():
    modules = (
        inspect.getmodule(InterventionPlanDialog),
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
        "START_INTERVENTION",
        "MARK_WAITING_REVIEW",
        "REVIEW_INTERVENTION",
        "CONTINUE_INTERVENTION",
    ):
        assert forbidden not in upper_source
