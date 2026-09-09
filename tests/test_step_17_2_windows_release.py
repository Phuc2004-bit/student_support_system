from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import zipfile


ROOT = Path(__file__).resolve().parent.parent
VERSION = "1.1.0"
PACKAGE_NAME = "StudentSupportSystem"
ZIP_NAME = f"{PACKAGE_NAME}-{VERSION}-win64.zip"


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def _test_environment_text() -> str:
    return "\n".join(
        "DB_NAME=student_support_db_test" if line.startswith("DB_NAME=") else line
        for line in read(".env.example").splitlines()
    ) + "\n"


def _sanitized_environment() -> dict[str, str]:
    environment = os.environ.copy()
    for key in tuple(environment):
        if (
            key.startswith("DB_")
            or key.startswith("APP_")
            or key in {"PYTHONHOME", "PYTHONPATH", "VIRTUAL_ENV", "QT_PLUGIN_PATH"}
        ):
            environment.pop(key)
    project = os.path.normcase(str(ROOT.resolve()))
    environment["PATH"] = os.pathsep.join(
        item
        for item in environment.get("PATH", "").split(os.pathsep)
        if project not in os.path.normcase(item)
        and ".venv" not in os.path.normcase(item)
    )
    environment.pop("QT_QPA_PLATFORM", None)
    environment.pop("MPLBACKEND", None)
    environment["PACKAGED_SMOKE_PREFIX"] = "T172"
    return environment


def test_v11_version_inputs_are_consistent():
    assert "APP_VERSION=1.1.0" in read(".env.example")
    assert '"1.1.0"' in read("config/settings.py")
    metadata = read("build_config/windows_version_info.txt")
    assert "filevers=(1, 1, 0, 0)" in metadata
    assert "prodvers=(1, 1, 0, 0)" in metadata
    assert "StringStruct('FileVersion', '1.1.0')" in metadata
    assert "StringStruct('ProductVersion', '1.1.0')" in metadata
    assert "StringStruct('ProductName', 'Student Support System')" in metadata
    assert "StringStruct('OriginalFilename', 'StudentSupportSystem.exe')" in metadata


def test_v11_spec_remains_windowed_onedir_without_speculative_collection():
    spec = read("StudentSupportSystem.spec")
    assert all(token in spec for token in ("Analysis(", "PYZ(", "EXE(", "COLLECT("))
    assert "exclude_binaries=True" in spec
    assert "console=False" in spec
    assert 'name="StudentSupportSystem"' in spec
    assert "hiddenimports=[]" in spec
    assert "binaries=[]" in spec
    assert "datas=[]" in spec
    assert "onefile" not in spec.casefold()


def test_v11_release_notes_checklist_and_deployment_guide_are_honest():
    notes = read("RELEASE_NOTES_V1.1.0.md")
    checklist = read("RELEASE_CHECKLIST_V1.1.0.md")
    guide = read("HUONG_DAN.txt")
    combined = "\n".join((notes, checklist, guide)).casefold()

    for expected in (
        "UI", "Login", "Students", "Scores", "Support", "Reports",
        "Catalog", "System", "initial ADMIN", "application lock", "1196 passed",
    ):
        assert expected.casefold() in notes.casefold()
    for expected in ("tests", "build", "ZIP", "checksum", "Git tag", "GitHub Release"):
        assert expected.casefold() in checklist.casefold()
    assert "python scripts/create_initial_admin.py" in guide
    assert "source checkout" in guide
    assert "không có đăng ký công" in guide
    for unsupported in ("auto updater included", "code signing included", "installer included"):
        assert unsupported not in combined


def test_v11_release_scripts_target_only_current_onedir_artifacts():
    build = read("scripts/build_windows.ps1")
    finalize = read("scripts/finalize_release.ps1")
    assert "StudentSupportSystem.spec" in build
    assert "StudentSupportSystem.exe" in build
    assert "Remove-Item -LiteralPath $Target -Recurse -Force" in build
    assert "StudentSupportSystem-1.1.0-win64.zip" in finalize
    assert "RELEASE_NOTES_V1.1.0.md" in finalize
    assert "RELEASE_CHECKLIST_V1.1.0.md" in finalize
    assert "StudentSupportSystem-1.0.0-win64.zip" not in finalize


def test_v11_final_package_contains_runtime_docs_and_no_forbidden_artifacts():
    package = ROOT / "dist" / PACKAGE_NAME
    required = {
        "StudentSupportSystem.exe",
        "_internal",
        ".env.example",
        "HUONG_DAN.txt",
        "RELEASE_NOTES_V1.1.0.md",
        "RELEASE_CHECKLIST_V1.1.0.md",
    }
    assert required.issubset({path.name for path in package.iterdir()})
    paths = tuple(path.relative_to(package) for path in package.rglob("*"))
    forbidden_parts = {"tests", ".git", ".venv", "__pycache__", "logs"}
    assert not any(
        any(part.casefold() in forbidden_parts for part in path.parts)
        for path in paths
    )
    assert not (package / ".env").exists()
    assert not any(path.suffix.casefold() in {".py", ".xlsx", ".log"} for path in paths)


def test_v11_zip_checksum_and_contents_are_self_consistent():
    zip_path = ROOT / "release" / ZIP_NAME
    checksum_path = ROOT / "release" / f"{ZIP_NAME}.sha256"
    expected_hash, filename = checksum_path.read_text(encoding="utf-8").strip().split("  ", 1)
    assert filename == ZIP_NAME
    assert hashlib.sha256(zip_path.read_bytes()).hexdigest() == expected_hash

    with zipfile.ZipFile(zip_path) as archive:
        names = tuple(archive.namelist())
    required = {
        f"{PACKAGE_NAME}/{PACKAGE_NAME}.exe",
        f"{PACKAGE_NAME}/.env.example",
        f"{PACKAGE_NAME}/HUONG_DAN.txt",
        f"{PACKAGE_NAME}/RELEASE_NOTES_V1.1.0.md",
        f"{PACKAGE_NAME}/RELEASE_CHECKLIST_V1.1.0.md",
    }
    assert required.issubset(names)
    assert any(name.startswith(f"{PACKAGE_NAME}/_internal/") for name in names)
    assert not any(name.endswith("/.env") for name in names)
    assert not any(name.casefold().endswith((".py", ".xlsx", ".log")) for name in names)
    assert not any(
        part.casefold() in {"tests", ".git", ".venv", "__pycache__", "logs"}
        for name in names
        for part in Path(name).parts
    )


def test_v11_extracted_zip_runs_core_smoke_from_clean_unicode_path(tmp_path):
    zip_path = ROOT / "release" / ZIP_NAME
    extraction_root = tmp_path / "Báº£n phÃ¢n phá»‘i V1.1 cÃ³ dáº¥u"
    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(extraction_root)

    package = extraction_root / PACKAGE_NAME
    executable = package / f"{PACKAGE_NAME}.exe"
    environment_file = package / ".env"
    result_path = tmp_path / "v11-extracted-smoke.json"
    environment_file.write_text(_test_environment_text(), encoding="utf-8")
    try:
        completed = subprocess.run(
            [str(executable), f"--packaged-functional-smoke={result_path}"],
            cwd=tmp_path,
            env=_sanitized_environment(),
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
        payload = (
            json.loads(result_path.read_text(encoding="utf-8"))
            if result_path.exists()
            else {}
        )
    finally:
        environment_file.unlink(missing_ok=True)

    assert completed.returncode == 0, {
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "payload": payload,
    }
    assert payload["fixture_prefix"] == "T172"
    assert payload["db_name"] == "student_support_db_test"
    assert payload["configured_db"] == "student_support_db_test"
    assert payload["app_version"] == VERSION
    assert payload["residual_counts"] == [0, 0, 0, 0, 0, 0]
    for required_check in (
        "admin_login",
        "v11_login_theme",
        "mainwindow_navigation",
        "v11_dark_theme",
        "students_page",
        "scores_page",
        "support_workflow",
        "reports_charts",
        "teacher_permissions",
        "teacher_logout_guard",
        "logout_relogin",
    ):
        assert payload[required_check] is True
