from __future__ import annotations

import inspect
import os
from pathlib import Path
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PIL import Image
from PySide6.QtWidgets import QApplication

from app_context import AppContext
from config.paths import PROJECT_ROOT
from models.dto import UserSession
from models.enums import UserRole
from services.permission_service import PermissionService
from ui import branding
from ui.dialogs.login_dialog import LoginDialog
from ui.main_window import MainWindow
from ui.widgets.sidebar import Sidebar


PNG_PATH = PROJECT_ROOT / "assets" / "app_icon.png"
ICO_PATH = PROJECT_ROOT / "assets" / "app_icon.ico"
EXPECTED_ICO_SIZES = {
    (16, 16),
    (24, 24),
    (32, 32),
    (48, 48),
    (64, 64),
    (128, 128),
    (256, 256),
}


def app() -> QApplication:
    return QApplication.instance() or QApplication([])


def context(role: UserRole = UserRole.ADMIN) -> AppContext:
    return AppContext(
        db=object(),
        auth_service=object(),
        permission_service=PermissionService(),
        session=UserSession(1, "actor", "Nguyễn Minh An", role),
    )


def test_official_icon_assets_exist_and_master_has_clean_transparency():
    assert PNG_PATH.is_file()
    assert ICO_PATH.is_file()

    with Image.open(PNG_PATH) as image:
        assert image.size == (1024, 1024)
        assert image.mode == "RGBA"
        alpha = image.getchannel("A")
        assert [
            alpha.getpixel(point)
            for point in ((0, 0), (1023, 0), (0, 1023), (1023, 1023))
        ] == [0, 0, 0, 0]
        left, top, right, bottom = alpha.getbbox()
        assert left >= 96 and top >= 96
        assert right <= 928 and bottom <= 928


def test_windows_ico_loads_and_contains_all_required_native_sizes():
    with Image.open(ICO_PATH) as image:
        assert image.format == "ICO"
        assert image.ico.sizes() == EXPECTED_ICO_SIZES
        for size in EXPECTED_ICO_SIZES:
            frame = image.ico.getimage(size)
            assert frame.size == size
            assert frame.getbbox() is not None


def test_generated_asset_origin_is_recorded_without_third_party_trademark():
    notice = (PROJECT_ROOT / "assets" / "README.md").read_text(encoding="utf-8")
    assert "project-owned generated assets" in notice
    assert "does not incorporate a third-party" in notice


def test_icon_resource_path_resolves_in_development_mode():
    assert branding.application_icon_path() == PNG_PATH


def test_icon_resource_path_resolves_in_frozen_mode(monkeypatch, tmp_path):
    bundle = tmp_path / "frozen bundle"
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(bundle), raising=False)

    assert branding.application_icon_path() == bundle.resolve() / "assets" / "app_icon.png"


def test_qapplication_uses_official_icon():
    application = app()
    icon = branding.configure_application_icon(application)

    assert not icon.isNull()
    assert not application.windowIcon().isNull()
    assert application.windowIcon().cacheKey() == icon.cacheKey()


def test_login_dialog_uses_compact_official_brand_mark():
    branding.configure_application_icon(app())
    dialog = LoginDialog(object())

    assert dialog.brand_mark_label.text() == ""
    assert dialog.brand_mark_label.pixmap() is not None
    assert not dialog.brand_mark_label.pixmap().isNull()
    assert "HỆ THỐNG" in dialog.title_label.text()
    dialog.close()


def test_sidebar_uses_same_brand_mark_without_changing_identity_text():
    branding.configure_application_icon(app())
    sidebar = Sidebar(session=context().session)

    assert sidebar.brand_mark_label.text() == ""
    assert sidebar.brand_mark_label.pixmap() is not None
    assert not sidebar.brand_mark_label.pixmap().isNull()
    assert sidebar.brand_title_label.text() == "Student Support"
    assert sidebar.brand_subtitle_label.text() == "Quản lý học tập"
    sidebar.close()


def test_main_window_branding_does_not_change_navigation_permissions():
    branding.configure_application_icon(app())
    admin_window = MainWindow(context())
    teacher_window = MainWindow(context(UserRole.TEACHER))

    assert all(admin_window.can_navigate_to(key) for key in MainWindow.PAGE_TITLES)
    assert teacher_window.can_navigate_to("students")
    assert teacher_window.can_navigate_to("system")
    assert not teacher_window.can_navigate_to("catalogs")
    assert not admin_window.windowIcon().isNull()
    assert not teacher_window.windowIcon().isNull()
    admin_window.close()
    teacher_window.close()


def test_pyinstaller_uses_official_icon_and_bundles_only_brand_assets():
    spec = (PROJECT_ROOT / "StudentSupportSystem.spec").read_text(encoding="utf-8")

    assert 'icon="assets/app_icon.ico"' in spec
    assert '("assets/app_icon.png", "assets")' in spec
    assert '("assets/app_icon.ico", "assets")' in spec
    assert "console=False" in spec
    assert "1.2.0" not in spec


def test_branding_layer_contains_no_business_or_data_access_logic():
    source = "\n".join(
        (
            inspect.getsource(branding),
            inspect.getsource(LoginDialog),
            inspect.getsource(Sidebar),
        )
    ).upper()

    assert "SELECT " not in source
    assert "INSERT " not in source
    assert "REPOSITORY" not in source
    assert "TRANSACTION(" not in source
