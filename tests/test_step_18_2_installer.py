from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parent.parent
ISS = ROOT / "installer" / "StudentSupportSystem.iss"
BUILD_SCRIPT = ROOT / "scripts" / "build_installer.ps1"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_inno_setup_script_exists_with_required_sections():
    assert ISS.is_file()
    source = read(ISS)
    for section in ("[Setup]", "[Files]", "[Icons]", "[Tasks]", "[Run]", "[Code]"):
        assert section in source


def test_installer_has_no_absolute_developer_path():
    assert not re.search(r"[A-Za-z]:[\\/]", read(ISS))


def test_installer_metadata_and_output_name_are_v13():
    source = read(ISS)
    assert '#define MyAppName "Student Support System"' in source
    assert '#define MyAppVersion "1.3.0"' in source
    assert "OutputBaseFilename=StudentSupportSystem-1.3.0-Setup" in source


def test_installer_uses_the_existing_onedir_package_only():
    source = read(ISS)
    assert '#define MyAppSourceDir "..\\dist\\StudentSupportSystem"' in source
    assert 'Source: "{#MyAppSourceDir}\\*"' in source
    assert "recursesubdirs" in source and "createallsubdirs" in source
    assert "main.py" not in source and ".venv" not in source


def test_installer_uses_official_icon_everywhere_relevant():
    source = read(ISS)
    assert "SetupIconFile=..\\assets\\app_icon.ico" in source
    assert "UninstallDisplayIcon={app}\\{#MyAppExeName}" in source
    assert source.count('IconFilename: "{app}\\{#MyAppExeName}"') == 2


def test_installer_is_per_user_and_x64_compatible():
    source = read(ISS)
    assert "DefaultDirName={localappdata}\\Programs\\StudentSupportSystem" in source
    assert "PrivilegesRequired=lowest" in source
    assert "ArchitecturesAllowed=x64compatible" in source
    assert "ArchitecturesInstallIn64BitMode=x64compatible" in source


def test_start_menu_and_uninstall_shortcuts_are_configured():
    source = read(ISS)
    assert "DefaultGroupName={#MyAppName}" in source
    assert 'Name: "{group}\\Student Support System"' in source
    assert 'Filename: "{uninstallexe}"' in source


def test_desktop_shortcut_is_optional_and_unchecked():
    source = read(ISS)
    assert 'Name: "desktopicon"' in source
    assert "Flags: unchecked" in source
    assert "Tasks: desktopicon" in source


def test_run_after_install_is_skipped_for_silent_install():
    source = read(ISS)
    assert "postinstall" in source
    assert "skipifsilent" in source


def test_uninstall_does_not_delete_external_user_data_or_database():
    source = read(ISS).casefold()
    assert "[uninstalldelete]" not in source
    assert "studentsupportsystem\\logs" not in source
    assert "drop database" not in source


def test_odbc_detection_warns_but_does_not_block_setup():
    source = read(ISS)
    assert "ODBC Driver 18 for SQL Server" in source
    assert "HKLM64" in source and "HKLM32" in source
    assert "Result := True" in source
    assert "MsgBox" in source


def test_real_env_is_never_selected_for_packaging():
    source = read(ISS)
    script = read(BUILD_SCRIPT)
    assert ".env.example" not in source
    assert 'Join-Path $PackageDir ".env"' in script
    assert "Refusing to build an installer containing a real .env file" in script


def test_installer_build_script_exists_and_validates_inputs():
    assert BUILD_SCRIPT.is_file()
    source = read(BUILD_SCRIPT)
    for required in (
        "Resolve-IsccCompiler", "ISCC.exe", "StudentSupportSystem.exe",
        "assets\\app_icon.ico", "dist\\StudentSupportSystem", "_internal",
    ):
        assert required in source


def test_build_script_never_downloads_inno_setup():
    source = read(BUILD_SCRIPT).casefold()
    for forbidden in ("invoke-webrequest", "start-bitstransfer", "curl.exe", "winget install"):
        assert forbidden not in source
    assert "this script never downloads prerequisites" in source


def test_build_script_validates_forbidden_content_and_reports_output():
    source = read(BUILD_SCRIPT)
    for forbidden in ("tests", ".git", ".venv", "__pycache__", "logs", ".xlsx", ".log"):
        assert f'"{forbidden}"' in source
    assert "StudentSupportSystem-1.3.0-Setup.exe" in source
    assert 'Write-Host "Installer:' in source
    assert 'Write-Host "Size:' in source


def test_version_is_synchronized_without_changing_product_identity():
    assert "APP_VERSION=1.3.0" in read(ROOT / ".env.example")
    assert '"1.3.0"' in read(ROOT / "config/settings.py")
    metadata = read(ROOT / "build_config/windows_version_info.txt")
    assert "filevers=(1, 3, 0, 0)" in metadata
    assert "prodvers=(1, 3, 0, 0)" in metadata
    assert "StringStruct('ProductName', 'Student Support System')" in metadata
    assert "StringStruct('OriginalFilename', 'StudentSupportSystem.exe')" in metadata


def test_prerequisite_and_initial_admin_policy_are_documented_safely():
    text = "\n".join(
        (
            read(ROOT / "installer/PREREQUISITES_V1.3.txt"),
            read(ROOT / "RELEASE_NOTES_V1.3.0.md"),
            read(ROOT / "HUONG_DAN.txt"),
        )
    ).casefold()
    for required in ("odbc driver 18", "sql server", "windows authentication", ".env.example"):
        assert required in text
    assert "scripts/create_initial_admin.py" in text


def test_installer_inputs_contain_no_hard_coded_credentials():
    source = "\n".join(
        read(path)
        for path in (
            ISS, BUILD_SCRIPT, ROOT / "installer/PREREQUISITES_V1.3.txt",
            ROOT / "RELEASE_NOTES_V1.3.0.md",
        )
    ).casefold()
    assert "password_hash" not in source
    assert "api_key" not in source
    assert not re.search(r"password\s*=", source)


def test_v12_release_artifacts_are_not_targeted_by_v13_scripts():
    installer = read(ISS)
    builder = read(BUILD_SCRIPT)
    finalizer = read(ROOT / "scripts/finalize_release.ps1")
    assert "1.2.0" not in installer + builder
    assert "StudentSupportSystem-1.3.0-win64.zip" in finalizer
    assert "StudentSupportSystem-1.2.0-win64.zip" not in finalizer
