from __future__ import annotations

from PySide6.QtWidgets import QMessageBox, QWidget

from services.support_contract import InterventionContinueServiceContract


def confirm_continue_support(
    parent: QWidget | None,
    service: InterventionContinueServiceContract,
    intervention_id: int,
) -> bool:
    answer = QMessageBox.question(
        parent,
        "Tiếp tục bổ trợ",
        "Tiếp tục thực hiện bổ trợ cho học sinh này?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    if answer != QMessageBox.StandardButton.Yes:
        return False

    service.continue_intervention(intervention_id)
    return True
