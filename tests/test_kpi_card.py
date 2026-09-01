import os

import pytest

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PySide6.QtWidgets import QApplication

from ui.widgets.kpi_card import KpiCard


def get_app() -> QApplication:
    app = QApplication.instance()

    if app is None:
        app = QApplication([])

    return app


def test_kpi_card_starts_at_zero():
    get_app()

    card = KpiCard(
        "Tổng học sinh"
    )

    assert card.title == "Tổng học sinh"
    assert card.value == 0
    assert card.value_label.text() == "0"


def test_kpi_card_updates_and_formats_value():
    get_app()

    card = KpiCard(
        "Tổng học sinh"
    )

    card.set_value(1000)

    assert card.value == 1000
    assert card.value_label.text() == "1.000"


@pytest.mark.parametrize(
    "value",
    [
        -1,
        True,
        1.5,
        "10",
        None,
    ],
)
def test_kpi_card_rejects_invalid_values(value):
    get_app()

    card = KpiCard(
        "KPI"
    )

    with pytest.raises(ValueError):
        card.set_value(value)


@pytest.mark.parametrize(
    "title",
    [
        "",
        "   ",
        None,
    ],
)
def test_kpi_card_rejects_blank_title(title):
    get_app()

    with pytest.raises(ValueError):
        KpiCard(title)
