from dataclasses import replace
from datetime import date
from decimal import Decimal
import inspect
import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialogButtonBox, QGridLayout

from models.enums import InterventionStatus, ReviewResult
from ui.dialogs.intervention_detail_dialog import InterventionDetailDialog
from ui.dialogs.intervention_plan_dialog import InterventionPlanDialog
from ui.dialogs.intervention_review_dialog import InterventionReviewDialog
from ui.pages.support_page import SupportPage
from ui.theme import (
    APP_BACKGROUND,
    BORDER,
    DANGER,
    PRIMARY,
    SUCCESS,
    WARNING,
    status_badge_colors,
    support_dialog_stylesheet,
    support_page_stylesheet,
)
from ui.widgets.support_filter_widget import SupportFilterWidget
from tests.test_step_11_intervention_detail import detail, review, report_row
from tests.test_step_11_intervention_planning import (
    PlanningServiceStub,
    UserServiceStub,
)
from tests.test_step_11_intervention_review import (
    AssessmentServiceStub,
    ReviewServiceStub,
)


def app():
    return QApplication.instance() or QApplication([])


def all_action_services():
    service = SimpleNamespace()
    return {
        "planning_service": service,
        "start_service": service,
        "waiting_review_service": service,
        "review_service": service,
        "continue_service": service,
        "assessment_service": service,
        "user_service": service,
    }


def test_support_theme_and_page_use_shared_dark_cards():
    app()
    page = SupportPage()
    stylesheet = page.styleSheet()

    assert page.filter_frame.objectName() == "supportFilterCard"
    assert page.table_frame.objectName() == "supportTableFrame"
    assert APP_BACKGROUND in stylesheet
    assert BORDER in stylesheet
    assert support_page_stylesheet() == stylesheet
    assert "supportFilterCard" in stylesheet
    assert "supportTableFrame" in stylesheet


def test_support_filters_use_compact_labeled_grid_without_semantic_change():
    app()
    widget = SupportFilterWidget()

    assert isinstance(widget.layout(), QGridLayout)
    assert widget.layout().columnCount() == 5
    assert widget.school_year_combo.objectName() == "supportSchoolYearFilter"
    assert widget.grade_combo.objectName() == "supportGradeFilter"
    assert widget.class_combo.objectName() == "supportClassFilter"
    assert widget.subject_combo.objectName() == "supportSubjectFilter"
    assert widget.status_combo.objectName() == "supportStatusFilter"
    assert [
        widget.status_combo.itemData(index)
        for index in range(1, widget.status_combo.count())
    ] == list(InterventionStatus)


@pytest.mark.parametrize(
    ("status", "expected_color"),
    [
        ("DETECTED", WARNING),
        ("PLANNED", PRIMARY),
        ("IN_PROGRESS", PRIMARY),
        ("WAITING_REVIEW", WARNING),
        ("CONTINUE", DANGER),
        ("COMPLETED", SUCCESS),
    ],
)
def test_intervention_table_renders_text_and_semantic_status_badge(
    status, expected_color
):
    app()
    page = SupportPage()

    page.set_support_cases([report_row() if status == "DETECTED" else replace(
        report_row(), status=status
    )])

    status_item = page.table.item(0, 8)
    assert status_item.text()
    assert status_item.data(Qt.ItemDataRole.UserRole + 1) == status
    assert status_item.foreground().color().name().upper() == expected_color
    assert page.table.verticalHeader().defaultSectionSize() == 40
    assert page.table.showGrid() is False
    assert page.table.horizontalHeader().sectionResizeMode(2) == (
        page.table.horizontalHeader().ResizeMode.Stretch
    )


@pytest.mark.parametrize(
    ("status", "visible_action", "message"),
    [
        (InterventionStatus.DETECTED, "plan_button", "lập kế hoạch"),
        (InterventionStatus.PLANNED, "start_button", "bắt đầu"),
        (
            InterventionStatus.IN_PROGRESS,
            "waiting_review_button",
            "quá trình bổ trợ",
        ),
        (
            InterventionStatus.WAITING_REVIEW,
            "review_button",
            "chờ đánh giá",
        ),
        (InterventionStatus.CONTINUE, "continue_button", "Cần tiếp tục"),
        (InterventionStatus.COMPLETED, None, "Đã đạt ngưỡng"),
    ],
)
def test_workflow_indicator_and_action_follow_saved_status(
    status, visible_action, message
):
    app()
    dialog = InterventionDetailDialog(
        101,
        SimpleNamespace(),
        **all_action_services(),
    )

    dialog._render_detail(replace(detail(), status=status))

    actions = {
        "plan_button": dialog.plan_button,
        "start_button": dialog.start_button,
        "waiting_review_button": dialog.waiting_review_button,
        "review_button": dialog.review_button,
        "continue_button": dialog.continue_button,
    }
    assert [name for name, button in actions.items() if not button.isHidden()] == (
        [visible_action] if visible_action else []
    )
    assert message.lower() in dialog.workflow_message_label.text().lower()
    assert dialog.status_value_label.property("interventionStatus") == status.value
    assert len(dialog.workflow_step_labels) == 5


def test_completed_is_read_only_and_has_no_manual_complete_control():
    app()
    dialog = InterventionDetailDialog(
        101,
        SimpleNamespace(),
        **all_action_services(),
    )
    dialog._render_detail(detail())

    assert not hasattr(dialog, "complete_button")
    assert all(
        "hoàn thành" not in button.text().lower()
        for button in dialog.findChildren(type(dialog.plan_button))
    )
    assert dialog.outcome_message_label.isHidden() is False
    assert "Không còn thao tác bổ trợ" in dialog.outcome_message_label.text()


def test_detail_card_renders_real_context_and_deterministic_review_history():
    app()
    reviews = (
        review(1, date(2026, 11, 1), Decimal("3.20")),
        review(2, date(2026, 11, 20), Decimal("4.20"), ReviewResult.PASSED),
    )
    dialog = InterventionDetailDialog(101, SimpleNamespace())

    dialog._render_detail(detail(reviews))

    assert dialog.identity_name_label.text() == "Student A"
    assert "HS001" in dialog.identity_context_label.text()
    assert "6A1" in dialog.identity_context_label.text()
    assert "Môn 1" in dialog.identity_context_label.text()
    assert dialog.trigger_assessment_label.text() == "Giữa kỳ"
    assert dialog.review_table.rowCount() == 2
    assert dialog.review_table.item(0, 0).text() == "01/11/2026"
    assert dialog.review_table.item(1, 0).text() == "20/11/2026"


def test_plan_dialog_uses_context_and_form_cards_with_primary_save():
    app()
    dialog = InterventionPlanDialog(
        detail(), PlanningServiceStub(), UserServiceStub()
    )
    save_button = dialog.buttons.button(QDialogButtonBox.StandardButton.Save)
    cancel_button = dialog.buttons.button(
        QDialogButtonBox.StandardButton.Cancel
    )

    assert dialog.styleSheet() == support_dialog_stylesheet()
    assert dialog.student_label.text() == "HS001 — Student A"
    assert save_button.text() == "Lưu kế hoạch"
    assert save_button.property("variant") == "primary"
    assert cancel_button.text() == "Hủy"


def test_review_dialog_explains_service_owned_result_and_preserves_input_contract():
    app()
    waiting = replace(detail(), status=InterventionStatus.WAITING_REVIEW)
    dialog = InterventionReviewDialog(
        waiting, ReviewServiceStub(), AssessmentServiceStub()
    )
    save_button = dialog.buttons.button(QDialogButtonBox.StandardButton.Save)

    assert dialog.student_label.text() == "HS001 — Student A"
    assert dialog.trigger_score_label.text() == "2.80"
    assert dialog.status_label.text() == "Chờ đánh giá"
    assert save_button.text() == "Lưu đánh giá"
    assert save_button.property("variant") == "primary"
    assert not hasattr(dialog, "result_combo")
    assert not hasattr(dialog, "status_combo")


def test_empty_state_and_permission_guard_remain_explicit():
    app()
    denied = SupportPage(excel_permission_check=lambda: False)
    allowed = SupportPage(excel_permission_check=lambda: True)

    denied.set_support_cases([])

    assert denied.empty_container.isHidden() is False
    assert denied.empty_label.text() == denied.EMPTY_MESSAGE
    assert denied.export_button.isHidden()
    assert not denied.export_button.isEnabled()
    assert not allowed.export_button.isHidden()
    assert allowed.export_button.isEnabled()


def test_support_presentation_has_no_business_or_data_layer_logic():
    modules = (
        inspect.getmodule(SupportPage),
        inspect.getmodule(SupportFilterWidget),
        inspect.getmodule(InterventionDetailDialog),
        inspect.getmodule(InterventionPlanDialog),
        inspect.getmodule(InterventionReviewDialog),
    )
    source = "\n".join(inspect.getsource(module) for module in modules)
    upper = source.upper()

    for forbidden in (
        "SELECT ",
        "INSERT ",
        "UPDATE ",
        "DELETE ",
        "REPOSITORY",
        "COMMIT(",
        "ROLLBACK(",
        "3.5",
        "COMPLETE_BUTTON",
    ):
        assert forbidden not in upper
    assert status_badge_colors("COMPLETED")[0] == SUCCESS
