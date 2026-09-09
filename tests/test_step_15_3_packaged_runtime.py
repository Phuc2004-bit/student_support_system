from __future__ import annotations

import ctypes
import json
import logging
import os
from pathlib import Path
import struct
import subprocess
import time

import pyodbc

import main as application_entry
from config.database import db_settings
from database.connection import DatabaseManager
from exceptions import ValidationError


ROOT = Path(__file__).resolve().parent.parent
RELEASE_DIR = ROOT / "dist" / "StudentSupportSystem"
EXECUTABLE = RELEASE_DIR / "StudentSupportSystem.exe"
DIST_ENV = RELEASE_DIR / ".env"
PREFIX = "T153"


def _test_connection_string() -> str:
    source = db_settings.connection_string()
    parts = []
    found = False
    for part in source.split(";"):
        if not part:
            continue
        if part.upper().startswith("DATABASE="):
            parts.append("DATABASE=student_support_db_test")
            found = True
        else:
            parts.append(part)
    assert found
    return ";".join(parts) + ";"


def _dist_environment_text() -> str:
    source = (ROOT / ".env.example").read_text(encoding="utf-8")
    lines = []
    replaced = False
    for line in source.splitlines():
        if line.startswith("DB_NAME="):
            lines.append("DB_NAME=student_support_db_test")
            replaced = True
        else:
            lines.append(line)
    assert replaced
    return "\n".join(lines) + "\n"


def _clean_subprocess_environment() -> dict[str, str]:
    environment = os.environ.copy()
    for key in tuple(environment):
        if key.startswith("DB_") or key.startswith("APP_"):
            environment.pop(key)
    environment.pop("QT_QPA_PLATFORM", None)
    environment.pop("QT_PLUGIN_PATH", None)
    environment.pop("MPLBACKEND", None)
    return environment


def _database_name_and_residuals() -> tuple[str, tuple[int, ...]]:
    connection_string = _test_connection_string()
    assert "DATABASE=student_support_db_test;" in connection_string
    connection = pyodbc.connect(connection_string, autocommit=False, timeout=5)
    try:
        cursor = connection.cursor()
        actual_name = str(cursor.execute("SELECT DB_NAME()").fetchone()[0])
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
        return actual_name, counts
    finally:
        connection.close()


def _application_log_path() -> Path:
    local_app_data = Path(os.environ["LOCALAPPDATA"])
    return local_app_data / "StudentSupportSystem" / "logs" / "app.log"


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


def test_packaged_smoke_argument_is_opt_in_and_normal_startup_stays_unchanged():
    assert application_entry.packaged_smoke_result_path([]) is None
    assert application_entry.packaged_smoke_result_path(["--unrelated"]) is None
    assert application_entry.packaged_smoke_result_path(
        ["--packaged-functional-smoke=C:/Temp/result.json"]
    ) == "C:/Temp/result.json"
    assert application_entry.packaged_smoke_result_path(
        ["--packaged-functional-smoke="]
    ) is None


def test_expected_application_error_rolls_back_without_error_traceback(
    monkeypatch, caplog
):
    class FakeConnection:
        rolled_back = False
        closed = False

        def rollback(self):
            self.rolled_back = True

        def commit(self):
            raise AssertionError("An unsuccessful transaction must not commit.")

        def close(self):
            self.closed = True

    connection = FakeConnection()
    manager = DatabaseManager("unused")
    monkeypatch.setattr(manager, "get_connection", lambda: connection)

    with caplog.at_level(logging.DEBUG, logger="database.connection"):
        try:
            with manager.transaction():
                raise ValidationError("expected validation failure")
        except ValidationError:
            pass

    assert connection.rolled_back is True
    assert connection.closed is True
    assert not [record for record in caplog.records if record.levelno >= logging.ERROR]
    assert all(record.exc_info is None for record in caplog.records)


def test_clean_onedir_contains_required_windows_runtime_artifacts():
    assert EXECUTABLE.is_file()
    assert (RELEASE_DIR / ".env.example").is_file()
    assert (RELEASE_DIR / "HUONG_DAN.txt").is_file()
    assert not DIST_ENV.exists()
    assert next(RELEASE_DIR.rglob("qwindows.dll"), None) is not None
    assert next(RELEASE_DIR.rglob("pyodbc*.pyd"), None) is not None
    assert next(RELEASE_DIR.rglob("_bcrypt.pyd"), None) is not None
    assert next(RELEASE_DIR.rglob("matplotlibrc"), None) is not None

    image = EXECUTABLE.read_bytes()
    pe_offset = struct.unpack_from("<I", image, 0x3C)[0]
    assert image[pe_offset:pe_offset + 4] == b"PE\0\0"
    subsystem = struct.unpack_from("<H", image, pe_offset + 24 + 68)[0]
    assert subsystem == 2  # IMAGE_SUBSYSTEM_WINDOWS_GUI


def test_packaged_normal_startup_displays_login_dialog_without_crashing():
    process = None
    try:
        DIST_ENV.write_text(_dist_environment_text(), encoding="utf-8")
        process = subprocess.Popen(
            [str(EXECUTABLE)],
            cwd=RELEASE_DIR,
            env=_clean_subprocess_environment(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
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
        if process is not None and process.poll() is None:
            process.terminate()
            process.wait(timeout=10)
        DIST_ENV.unlink(missing_ok=True)


def test_packaged_exe_functional_smoke_uses_only_test_database_and_cleans_up(
    tmp_path,
):
    assert EXECUTABLE.is_file()
    assert not DIST_ENV.exists()
    actual_name, initial_counts = _database_name_and_residuals()
    assert actual_name == "student_support_db_test"
    assert initial_counts == (0, 0, 0, 0, 0, 0)

    result_path = tmp_path / "packaged-smoke-result.json"
    log_path = _application_log_path()
    old_log_size = log_path.stat().st_size if log_path.exists() else 0
    completed = None
    payload: dict[str, object] = {}
    try:
        DIST_ENV.write_text(_dist_environment_text(), encoding="utf-8")
        completed = subprocess.run(
            [str(EXECUTABLE), f"--packaged-functional-smoke={result_path}"],
            cwd=RELEASE_DIR,
            env=_clean_subprocess_environment(),
            capture_output=True,
            text=True,
            timeout=240,
            check=False,
        )
        if result_path.exists():
            payload = json.loads(result_path.read_text(encoding="utf-8"))
    finally:
        DIST_ENV.unlink(missing_ok=True)

    assert completed is not None
    assert completed.returncode == 0, {
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "payload": payload,
    }
    assert payload["frozen"] is True
    assert Path(str(payload["env_file"])).resolve() == DIST_ENV.resolve()
    assert payload["configured_db"] == "student_support_db_test"
    assert payload["app_version"] == "1.2.0"
    assert payload["db_name"] == "student_support_db_test"
    assert payload["residual_counts"] == [0, 0, 0, 0, 0, 0]

    excluded = {
        "env_file", "executable", "working_directory", "runtime_paths",
        "fixture_prefix", "configured_db", "db_name", "app_version",
        "excel_files",
        "residual_counts",
    }
    boolean_checks = {
        key: value for key, value in payload.items() if key not in excluded
    }
    assert boolean_checks
    assert all(value is True for value in boolean_checks.values()), boolean_checks
    assert payload["fixture_prefix"] == "T153"

    excel_files = [Path(item) for item in payload["excel_files"]]
    assert len(excel_files) == 5
    assert all(path.parent == tmp_path and path.is_file() for path in excel_files)

    assert log_path.is_file()
    with log_path.open("rb") as stream:
        stream.seek(old_log_size)
        new_log = stream.read().decode("utf-8", errors="replace")
    assert "Application starting" in new_log
    assert "Packaged functional smoke completed" in new_log
    assert "traceback" not in new_log.lower()
    for forbidden in (
        "password",
        "password_hash",
        "db_password",
        "pwd=",
        "T153OldPassword!",
        "T153NewPassword!",
        "DRIVER={",
    ):
        assert forbidden.lower() not in new_log.lower()

    final_name, final_counts = _database_name_and_residuals()
    assert final_name == "student_support_db_test"
    assert final_counts == (0, 0, 0, 0, 0, 0)
    assert not DIST_ENV.exists()
    assert not list(ROOT.rglob("T153*.xlsx"))
