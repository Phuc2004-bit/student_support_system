import os

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PySide6.QtWidgets import QApplication

from models.dto.dashboard_dto import DashboardSummary
from ui.pages.dashboard_page import DashboardPage
from ui.widgets.kpi_card import KpiCard


def get_app() -> QApplication:
    app = QApplication.instance()

    if app is None:
        app = QApplication([])

    return app


def make_summary() -> DashboardSummary:
    return DashboardSummary(
        total_students=1000,
        needs_support_count=120,
        in_progress_count=50,
        waiting_review_count=20,
        completed_count=40,
        continue_count=10,
    )


def test_dashboard_page_creates_exactly_six_kpi_cards():
    get_app()

    page = DashboardPage()

    assert set(
        page.kpi_cards
    ) == {
        "total_students",
        "needs_support_count",
        "in_progress_count",
        "waiting_review_count",
        "completed_count",
        "continue_count",
    }

    assert len(
        page.kpi_cards
    ) == 6

    assert all(
        isinstance(card, KpiCard)
        for card in page.kpi_cards.values()
    )


def test_dashboard_kpi_titles_match_v1_specification():
    get_app()

    page = DashboardPage()

    assert (
        page.kpi_cards[
            "total_students"
        ].title
        == "Tổng học sinh"
    )
    assert (
        page.kpi_cards[
            "needs_support_count"
        ].title
        == "Cần bổ trợ"
    )
    assert (
        page.kpi_cards[
            "in_progress_count"
        ].title
        == "Đang bổ trợ"
    )
    assert (
        page.kpi_cards[
            "waiting_review_count"
        ].title
        == "Chờ đánh giá"
    )
    assert (
        page.kpi_cards[
            "completed_count"
        ].title
        == "Đã đạt ngưỡng"
    )
    assert (
        page.kpi_cards[
            "continue_count"
        ].title
        == "Cần tiếp tục"
    )


def test_set_summary_binds_all_six_values():
    get_app()

    page = DashboardPage()

    page.set_summary(
        make_summary()
    )

    assert (
        page.kpi_cards[
            "total_students"
        ].value
        == 1000
    )
    assert (
        page.kpi_cards[
            "needs_support_count"
        ].value
        == 120
    )
    assert (
        page.kpi_cards[
            "in_progress_count"
        ].value
        == 50
    )
    assert (
        page.kpi_cards[
            "waiting_review_count"
        ].value
        == 20
    )
    assert (
        page.kpi_cards[
            "completed_count"
        ].value
        == 40
    )
    assert (
        page.kpi_cards[
            "continue_count"
        ].value
        == 10
    )


def test_set_summary_formats_large_student_count():
    get_app()

    page = DashboardPage()

    page.set_summary(
        make_summary()
    )

    assert (
        page.kpi_cards[
            "total_students"
        ].value_label.text()
        == "1.000"
    )
