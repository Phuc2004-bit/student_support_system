from __future__ import annotations

from PySide6.QtWidgets import (
    QStackedWidget,
    QWidget,
)


class PageStack(QStackedWidget):
    """
    QStackedWidget có registry key -> QWidget.

    Không chứa business logic.
    """

    def __init__(
        self,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.setObjectName("pageStack")
        self._pages: dict[str, QWidget] = {}

    @property
    def current_key(self) -> str | None:
        current = self.currentWidget()

        if current is None:
            return None

        for key, page in self._pages.items():
            if page is current:
                return key

        return None

    def register_page(
        self,
        key: str,
        page: QWidget,
    ) -> None:
        normalized_key = key.strip()

        if not normalized_key:
            raise ValueError(
                "Page key không được để trống."
            )

        if normalized_key in self._pages:
            raise ValueError(
                f"Page key đã tồn tại: {normalized_key}"
            )

        if page is None:
            raise ValueError(
                "Page widget không được để trống."
            )

        self._pages[normalized_key] = page
        self.addWidget(page)

    def page(
        self,
        key: str,
    ) -> QWidget:
        try:
            return self._pages[key]
        except KeyError as exc:
            raise KeyError(
                f"Không tồn tại page: {key}"
            ) from exc

    def show_page(
        self,
        key: str,
    ) -> None:
        page = self.page(key)
        self.setCurrentWidget(page)
