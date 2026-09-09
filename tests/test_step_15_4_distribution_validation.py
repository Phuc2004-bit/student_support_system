from __future__ import annotations

import ctypes
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

import pyodbc

from config.database import db_settings


ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist" / "StudentSupportSystem"
EXECUTABLE_NAME = "StudentSupportSystem.exe"
PREFIX = "T154"


def _environment_text() -> str:
    lines = []
    for line in (ROOT / ".env.example").read_text(encoding="utf-8").splitlines():
        lines.append(
            "DB_NAME=student_support_db_test"
            if line.startswith("DB_NAME=")
            else line
        )
    return "\n".join(lines) + "\n"


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
    environment["PACKAGED_SMOKE_PREFIX"] = PREFIX
    return environment


def _test_connection_string() -> str:
    parts = []
    for part in db_settings.connection_string().split(";"):
        if not part:
            continue
        parts.append(
            "DATABASE=student_support_db_test"
            if part.upper().startswith("DATABASE=")
            else part
        )
    return ";".join(parts) + ";"


def _database_audit() -> tuple[str, tuple[int, ...]]:
    connection = pyodbc.connect(
        _test_connection_string(), autocommit=False, timeout=5
    )
    try:
        cursor = connection.cursor()
        database_name = str(cursor.execute("SELECT DB_NAME()").fetchone()[0])
        checks = (
            ("dbo.USERS", "username LIKE ?", f"{PREFIX.lower()}%"),
            ("dbo.STUDENTS", "student_code LIKE ?", f"{PREFIX}%"),
            ("dbo.SCHOOL_YEARS", "year_name LIKE ?", f"{PREFIX}%"),
            ("dbo.CLASSES", "class_name LIKE ?", f"{PREFIX}%"),
            ("dbo.SUBJECTS", "subject_code LIKE ?", f"{PREFIX}%"),
            ("dbo.ASSESSMENTS", "assessment_name LIKE ?", f"{PREFIX}%"),
        )
        counts = tuple(
            int(
                cursor.execute(
                    f"SELECT COUNT(*) FROM {table} WHERE {where}", value
                ).fetchone()[0]
            )
            for table, where, value in checks
        )
        connection.rollback()
        return database_name, counts
    finally:
        connection.close()


def _visible_window_titles(process_id: int) -> tuple[str, ...]:
    titles: list[str] = []
    user32 = ctypes.windll.user32
    callback_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def collect(window, _parameter):
        window_process_id = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(window, ctypes.byref(window_process_id))
        if window_process_id.value != process_id or not user32.IsWindowVisible(window):
            return True
        length = user32.GetWindowTextLengthW(window)
        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(window, buffer, len(buffer))
        if buffer.value:
            titles.append(buffer.value)
        return True

    user32.EnumWindows(callback_type(collect), 0)
    return tuple(titles)


def _assert_login_dialog(executable: Path, cwd: Path, environment: dict[str, str]):
    process = subprocess.Popen(
        [str(executable)],
        cwd=cwd,
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.monotonic() + 15
        titles: tuple[str, ...] = ()
        while time.monotonic() < deadline and process.poll() is None:
            titles = _visible_window_titles(process.pid)
            if "Đăng nhập" in titles:
                break
            time.sleep(0.1)
        assert process.poll() is None
        assert "Đăng nhập" in titles
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=10)


def _run_functional_smoke(
    executable: Path,
    cwd: Path,
    output_dir: Path,
    environment: dict[str, str],
) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    result_path = output_dir / "result.json"
    completed = subprocess.run(
        [str(executable), f"--packaged-functional-smoke={result_path}"],
        cwd=cwd,
        env=environment,
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
    assert completed.returncode == 0, {
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "payload": payload,
    }
    assert payload["fixture_prefix"] == PREFIX
    assert payload["db_name"] == "student_support_db_test"
    assert payload["configured_db"] == "student_support_db_test"
    assert payload["app_version"] == "1.2.0"
    assert payload["residual_counts"] == [0, 0, 0, 0, 0, 0]
    excluded = {
        "env_file", "executable", "working_directory", "runtime_paths",
        "fixture_prefix", "db_name", "configured_db", "app_version",
        "excel_files",
        "residual_counts",
    }
    assert all(value is True for key, value in payload.items() if key not in excluded)
    return payload


def test_distribution_contents_and_user_guide_are_self_contained():
    assert (DIST / EXECUTABLE_NAME).is_file()
    assert (DIST / "_internal").is_dir()
    assert (DIST / ".env.example").is_file()
    assert (DIST / "HUONG_DAN.txt").is_file()
    assert not (DIST / ".env").exists()

    relative_paths = tuple(path.relative_to(DIST) for path in DIST.rglob("*"))
    forbidden_parts = {"tests", "pytest", ".git", ".venv", "__pycache__"}
    assert not any(
        any(part.casefold() in forbidden_parts for part in path.parts)
        for path in relative_paths
    )
    assert not any(path.suffix.casefold() == ".py" for path in relative_paths)
    assert not any(path.suffix.casefold() == ".xlsx" for path in relative_paths)

    guide = (DIST / "HUONG_DAN.txt").read_text(encoding="utf-8")
    for required in (
        "Windows 64-bit",
        "ODBC Driver 18 for SQL Server",
        ".env.example",
        "StudentSupportSystem.exe",
        "%LOCALAPPDATA%\\StudentSupportSystem\\logs\\app.log",
    ):
        assert required in guide


def test_isolated_distribution_is_cwd_source_venv_and_location_independent(
    tmp_path,
):
    assert "ODBC Driver 18 for SQL Server" in pyodbc.drivers()
    database_name, initial_counts = _database_audit()
    assert database_name == "student_support_db_test"
    assert initial_counts == (0, 0, 0, 0, 0, 0)

    validation_root = tmp_path / "Student Support System 15.4 Validation"
    location_a = validation_root / "Student Support System A"
    location_b = validation_root / "Phần mềm hỗ trợ học sinh B"
    launch_cwd = validation_root / "working directory độc lập"
    output_a = validation_root / "output A"
    output_b = validation_root / "kết quả B"
    environment = _sanitized_environment()
    log_path = Path(environment["LOCALAPPDATA"]) / "StudentSupportSystem" / "logs" / "app.log"
    old_log_size = log_path.stat().st_size if log_path.exists() else 0

    location_a.parent.mkdir(parents=True)
    launch_cwd.mkdir()
    shutil.copytree(DIST, location_a)
    env_a = location_a / ".env"
    env_b = location_b / ".env"
    try:
        env_a.write_text(_environment_text(), encoding="utf-8")
        executable_a = location_a / EXECUTABLE_NAME
        _assert_login_dialog(executable_a, launch_cwd, environment)
        payload_a = _run_functional_smoke(
            executable_a, launch_cwd, output_a, environment
        )
        assert Path(str(payload_a["env_file"])).resolve() == env_a.resolve()
        assert Path(str(payload_a["executable"])).resolve() == executable_a.resolve()
        assert Path(str(payload_a["working_directory"])).resolve() == launch_cwd.resolve()

        env_a.unlink()
        shutil.move(str(location_a), str(location_b))
        executable_b = location_b / EXECUTABLE_NAME

        missing_result = output_b / "missing-env-result.json"
        output_b.mkdir(parents=True)
        missing = subprocess.run(
            [str(executable_b), f"--packaged-functional-smoke={missing_result}"],
            cwd=launch_cwd,
            env=environment,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        missing_payload = json.loads(missing_result.read_text(encoding="utf-8"))
        assert missing.returncode == 1
        assert missing_payload == {"error_type": "RuntimeError"}
        assert "traceback" not in missing.stderr.casefold()

        env_b.write_text(_environment_text(), encoding="utf-8")
        payload_b = _run_functional_smoke(
            executable_b, launch_cwd, output_b / "functional", environment
        )
        assert Path(str(payload_b["env_file"])).resolve() == env_b.resolve()
        assert Path(str(payload_b["executable"])).resolve() == executable_b.resolve()
        assert Path(str(payload_b["working_directory"])).resolve() == launch_cwd.resolve()
        runtime_paths = "\n".join(str(item) for item in payload_b["runtime_paths"])
        assert str(ROOT.resolve()).casefold() not in runtime_paths.casefold()
        assert ".venv" not in runtime_paths.casefold()
        assert all(Path(item).name.startswith(PREFIX) for item in payload_b["excel_files"])

        assert not list(location_b.rglob("*.xlsx"))
        assert not (location_b / "app.log").exists()
        assert not (launch_cwd / "app.log").exists()
        assert log_path.is_file()
        with log_path.open("rb") as stream:
            stream.seek(old_log_size)
            new_log = stream.read().decode("utf-8", errors="replace")
        assert "Application starting" in new_log
        assert "Packaged functional smoke completed" in new_log
        for forbidden in (
            "password_hash", "db_password", "pwd=",
            f"{PREFIX}OldPassword!", f"{PREFIX}NewPassword!", "DRIVER={",
        ):
            assert forbidden.casefold() not in new_log.casefold()

        final_name, final_counts = _database_audit()
        assert final_name == "student_support_db_test"
        assert final_counts == (0, 0, 0, 0, 0, 0)
    finally:
        env_a.unlink(missing_ok=True)
        env_b.unlink(missing_ok=True)
        shutil.rmtree(validation_root, ignore_errors=True)

    assert not validation_root.exists()
    assert not (DIST / ".env").exists()
    assert not list(ROOT.rglob(f"{PREFIX}*.xlsx"))
    assert not [
        process
        for process in _running_process_names()
        if process.casefold() == EXECUTABLE_NAME.casefold()
    ]


def _running_process_names() -> tuple[str, ...]:
    completed = subprocess.run(
        [
            "powershell", "-NoProfile", "-Command",
            "@(Get-Process -Name 'StudentSupportSystem' -ErrorAction SilentlyContinue).ProcessName",
        ],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    return tuple(line.strip() + ".exe" for line in completed.stdout.splitlines() if line.strip())
