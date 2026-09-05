from __future__ import annotations

from collections.abc import Callable


PermissionCheck = Callable[[], bool]


def action_is_allowed(check: PermissionCheck | None) -> bool:
    if check is None:
        return True
    try:
        return bool(check())
    except Exception:
        return False


def apply_action_permission(button, check: PermissionCheck | None) -> None:
    allowed = action_is_allowed(check)
    button.setVisible(allowed)
    button.setEnabled(allowed)
