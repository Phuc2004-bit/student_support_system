from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import zipfile


ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist" / "StudentSupportSystem"
EXE = DIST / "StudentSupportSystem.exe"
RELEASE_NOTES = ROOT / "RELEASE_NOTES_V1.0.0.md"
RELEASE_CHECKLIST = ROOT / "RELEASE_CHECKLIST_V1.0.0.md"
ZIP_NAME = "StudentSupportSystem-1.0.0-win64.zip"
ZIP_PATH = ROOT / "release" / ZIP_NAME
CHECKSUM_PATH = ROOT / "release" / f"{ZIP_NAME}.sha256"
PREFIX = "T155"


def _test_environment() -> dict[str, str]:
    environment = os.environ.copy()
    for key in tuple(environment):
        if key.startswith("DB_") or key.startswith("APP_"):
            environment.pop(key)
        if key in {"PYTHONHOME", "PYTHONPATH", "VIRTUAL_ENV", "QT_PLUGIN_PATH"}:
            environment.pop(key)
    project = os.path.normcase(str(ROOT.resolve()))
    environment["PATH"] = os.pathsep.join(
        value
        for value in environment.get("PATH", "").split(os.pathsep)
        if project not in os.path.normcase(value)
        and ".venv" not in os.path.normcase(value)
    )
    environment.pop("QT_QPA_PLATFORM", None)
    environment.pop("MPLBACKEND", None)
    environment["PACKAGED_SMOKE_PREFIX"] = PREFIX
    return environment


def _test_env_text() -> str:
    source = (ROOT / ".env.example").read_text(encoding="utf-8")
    return source.replace(
        "DB_NAME=student_support_db\n",
        "DB_NAME=student_support_db_test\n",
    )


def test_release_version_documentation_and_build_inputs_are_consistent():
    assert RELEASE_NOTES.is_file()
    assert RELEASE_CHECKLIST.is_file()
    notes = RELEASE_NOTES.read_text(encoding="utf-8")
    checklist = RELEASE_CHECKLIST.read_text(encoding="utf-8")
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
    runtime = (ROOT / "requirements-runtime.txt").read_text(encoding="utf-8")
    dev = (ROOT / "requirements-dev.txt").read_text(encoding="utf-8")

    assert "Student Support System 1.0.0" in notes
    assert "1080 passed, 0 failed, 0 errors" in notes
    assert "separate clean physical Windows machine or VM" in notes
    assert "PENDING" in checklist
    assert "tested on a clean machine" not in (notes + checklist).casefold()
    assert "DB_NAME=student_support_db\n" in env_example
    assert "student_support_db_test" not in env_example
    assert all(
        value in runtime
        for value in (
            "PySide6==6.11.2", "pyodbc==5.3.0", "openpyxl==3.1.5",
            "matplotlib==3.11.1", "bcrypt==5.0.0", "python-dotenv==1.2.3",
        )
    )
    assert "PyInstaller==6.22.2" in dev
    assert "release/" in (ROOT / ".gitignore").read_text(encoding="utf-8")

    metadata = (ROOT / "build_config" / "windows_version_info.txt").read_text(
        encoding="utf-8"
    )
    assert "1.0.0" in metadata
    assert "Student Support System" in metadata
    assert "StringStruct('CompanyName', '')" in metadata


def test_final_dist_packaged_smoke_uses_t155_and_leaves_release_clean(tmp_path):
    assert EXE.is_file()
    dist_env = DIST / ".env"
    result_path = tmp_path / "T155-final-smoke.json"
    assert not dist_env.exists()
    try:
        dist_env.write_text(_test_env_text(), encoding="utf-8")
        completed = subprocess.run(
            [str(EXE), f"--packaged-functional-smoke={result_path}"],
            cwd=tmp_path,
            env=_test_environment(),
            capture_output=True,
            text=True,
            timeout=240,
            check=False,
        )
        payload = (
            json.loads(result_path.read_text(encoding="utf-8"))
            if result_path.exists()
            else {}
        )
    finally:
        dist_env.unlink(missing_ok=True)

    assert completed.returncode == 0, {
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "payload": payload,
    }
    assert payload["fixture_prefix"] == PREFIX
    assert payload["db_name"] == "student_support_db_test"
    assert payload["configured_db"] == "student_support_db_test"
    assert payload["residual_counts"] == [0, 0, 0, 0, 0, 0]
    assert all(Path(path).is_file() for path in payload["excel_files"])
    assert not dist_env.exists()
    assert not list(DIST.rglob("*.xlsx"))


def test_final_zip_structure_checksum_and_extracted_startup(tmp_path):
    assert ZIP_PATH.is_file()
    assert CHECKSUM_PATH.is_file()
    checksum_line = CHECKSUM_PATH.read_text(encoding="utf-8").strip()
    expected_hash, filename = checksum_line.split("  ", 1)
    assert filename == ZIP_NAME
    assert len(expected_hash) == 64
    actual_hash = hashlib.sha256(ZIP_PATH.read_bytes()).hexdigest()
    assert actual_hash == expected_hash

    with zipfile.ZipFile(ZIP_PATH) as archive:
        names = tuple(archive.namelist())
        required = {
            "StudentSupportSystem/StudentSupportSystem.exe",
            "StudentSupportSystem/.env.example",
            "StudentSupportSystem/HUONG_DAN.txt",
            "StudentSupportSystem/RELEASE_NOTES_V1.0.0.md",
            "StudentSupportSystem/RELEASE_CHECKLIST_V1.0.0.md",
        }
        assert required.issubset(names)
        assert any(name.startswith("StudentSupportSystem/_internal/") for name in names)
        assert not any(name.endswith("/.env") or name == "StudentSupportSystem/.env" for name in names)
        assert not any(name.casefold().endswith((".py", ".xlsx", ".log")) for name in names)
        assert not any(
            part.casefold() in {"tests", "pytest", ".git", ".venv", "build"}
            for name in names
            for part in Path(name).parts
        )
        assert all(".." not in Path(name).parts for name in names)
        archive.extractall(tmp_path)

    extracted = tmp_path / "StudentSupportSystem"
    extracted_exe = extracted / "StudentSupportSystem.exe"
    assert extracted_exe.is_file()
    assert (extracted / ".env.example").is_file()
    assert not (extracted / ".env").exists()

    result_path = tmp_path / "extracted-no-env-result.json"
    completed = subprocess.run(
        [str(extracted_exe), f"--packaged-functional-smoke={result_path}"],
        cwd=tmp_path,
        env=_test_environment(),
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert completed.returncode == 1
    assert payload == {"error_type": "RuntimeError"}
    assert "traceback" not in completed.stderr.casefold()
