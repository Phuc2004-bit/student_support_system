import os

import pytest

os.environ.setdefault(
    "QT_QPA_PLATFORM",
    "offscreen",
)

from PySide6.QtWidgets import (
    QApplication,
    QWidget,
)

from ui.widgets.page_stack import PageStack


def get_app() -> QApplication:
    app = QApplication.instance()

    if app is None:
        app = QApplication([])

    return app


def test_page_stack_registers_and_returns_page():
    get_app()

    stack = PageStack()
    page = QWidget()

    stack.register_page(
        "dashboard",
        page,
    )

    assert (
        stack.page("dashboard")
        is page
    )


def test_page_stack_switches_by_key():
    get_app()

    stack = PageStack()

    first = QWidget()
    second = QWidget()

    stack.register_page(
        "dashboard",
        first,
    )
    stack.register_page(
        "students",
        second,
    )

    stack.show_page("students")

    assert stack.currentWidget() is second
    assert stack.current_key == "students"


def test_page_stack_rejects_duplicate_key():
    get_app()

    stack = PageStack()

    stack.register_page(
        "dashboard",
        QWidget(),
    )

    with pytest.raises(ValueError):
        stack.register_page(
            "dashboard",
            QWidget(),
        )


def test_page_stack_rejects_unknown_key():
    get_app()

    stack = PageStack()

    with pytest.raises(KeyError):
        stack.show_page("unknown")


def test_page_stack_rejects_blank_key():
    get_app()

    stack = PageStack()

    with pytest.raises(ValueError):
        stack.register_page(
            "   ",
            QWidget(),
        )
