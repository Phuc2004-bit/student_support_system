import os
from datetime import date
from decimal import Decimal

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from models.dto.dashboard_dto import DashboardAttentionItem
from ui.widgets.dashboard_attention import DashboardAttentionTable


def get_app():
    app = QApplication.instance()
    return app or QApplication([])


def make_item(
    intervention_id=101,
    status="WAITING_REVIEW",
    latest_review_score=Decimal("3.20"),
):
    return DashboardAttentionItem(
        intervention_id=intervention_id,
        student_code="HS001",
        full_name="Nguyễn Văn A",
        grade_number=6,
        class_name="6A1",
        subject_code="TOAN",
        subject_name="Toán",
        status=status,
        detected_date=date(2026, 9, 15),
        trigger_score=Decimal("2.80"),
        latest_review_score=latest_review_score,
    )


def test_attention_table_starts_empty():
    get_app()
    widget = DashboardAttentionTable()

    assert widget.items == ()
    assert widget.table.rowCount() == 0
    assert widget.empty_label.isVisible() is False or widget.empty_label.text()


def test_attention_table_renders_one_item():
    get_app()
    widget = DashboardAttentionTable()
    widget.set_items((make_item(),))

    assert widget.table.rowCount() == 1
    assert widget.table.item(0, 0).text() == "HS001"
    assert widget.table.item(0, 1).text() == "Nguyễn Văn A"
    assert widget.table.item(0, 4).text() == "Chờ đánh giá"


def test_attention_table_formats_dates_and_scores():
    get_app()
    widget = DashboardAttentionTable()
    widget.set_items((make_item(),))

    assert widget.table.item(0, 5).text() == "15/09/2026"
    assert widget.table.item(0, 6).text() == "2.80"
    assert widget.table.item(0, 7).text() == "3.20"


def test_attention_table_uses_dash_when_no_latest_review():
    get_app()
    widget = DashboardAttentionTable()
    widget.set_items(
        (make_item(latest_review_score=None),)
    )

    assert widget.table.item(0, 7).text() == "—"


def test_attention_table_returns_intervention_id_for_row():
    get_app()
    widget = DashboardAttentionTable()
    widget.set_items(
        (
            make_item(intervention_id=101),
            make_item(intervention_id=202),
        )
    )

    assert widget.intervention_id_at_row(0) == 101
    assert widget.intervention_id_at_row(1) == 202
    assert widget.intervention_id_at_row(2) is None
