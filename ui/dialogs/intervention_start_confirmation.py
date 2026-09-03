from __future__ import annotations

from PySide6.QtWidgets import QMessageBox, QWidget

from services.support_contract import InterventionStartServiceContract


def confirm_begin_support(
    parent: QWidget,
    service: InterventionStartServiceContract,
    intervention_id: int,
) -> bool:
    answer = QMessageBox.question(
        parent,
        "Bắt đầu bổ trợ",
        "Bắt đầu thực hiện kế hoạch bổ trợ cho học sinh này?",
        QMessageBox.StandardButton.Yes
        | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    if answer != QMessageBox.StandardButton.Yes:
        return False

    service.start_intervention(intervention_id)
    return True
