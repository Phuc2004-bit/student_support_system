from __future__ import annotations

import inspect
import logging
import os
from pathlib import Path
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pyodbc
import pytest

import main as application_entry
from config.database import db_settings
from config.logging_config import setup_logging
from config.paths import (
    PRODUCT_DIRECTORY,
    PROJECT_ROOT,
    application_dir,
    environment_file_path,
    resource_path,
    user_data_dir,
)
from config.settings import settings
from database.connection import DatabaseManager
from exceptions import DatabaseError
from services import (
    data_export_service,
    report_export_service,
    score_import_parser,
    score_import_template_service,
)


def close_application_log_handlers() -> None:
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        if getattr(handler, "student_support_handler", False):
            root_logger.removeHandler(handler)
            handler.close()


def test_production_entry_point_is_importable_and_uses_existing_bootstrap_flow():
    source = inspect.getsource(application_entry)

    assert callable(application_entry.main)
    assert callable(application_entry.run)
    assert "build_app_context()" in source
    assert "run_application_flow" in source
    assert 'if __name__ == "__main__"' in source
    assert "SystemExit(run())" in source


def test_development_config_and_production_database_default_are_safe():
    assert application_dir() == PROJECT_ROOT
    assert environment_file_path() == PROJECT_ROOT / ".env"
    # The ignored developer .env may override the release default. Release
    # version consistency is validated from committed inputs in Step 17.2.
    assert settings.APP_VERSION == os.getenv("APP_VERSION", "1.1.0")
    assert db_settings.DATABASE == "student_support_db"
    assert "DATABASE=student_support_db_test;" not in db_settings.connection_string()

    test_connection = db_settings.connection_string().replace(
        "DATABASE=student_support_db;", "DATABASE=student_support_db_test;"
    )
    assert "DATABASE=student_support_db_test;" in test_connection


def test_resource_paths_support_development_and_frozen_modes(monkeypatch, tmp_path):
    assert resource_path("assets", "app.ico") == PROJECT_ROOT / "assets" / "app.ico"

    executable = tmp_path / "install" / "StudentSupportSystem.exe"
    bundle = tmp_path / "bundle"
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(executable))
    monkeypatch.setattr(sys, "_MEIPASS", str(bundle), raising=False)

    assert application_dir() == executable.parent.resolve()
    assert environment_file_path() == executable.parent.resolve() / ".env"
    assert resource_path("assets", "app.ico") == bundle.resolve() / "assets" / "app.ico"


def test_writable_paths_use_windows_local_app_data(monkeypatch, tmp_path):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))

    assert user_data_dir() == tmp_path / PRODUCT_DIRECTORY
    assert not settings.LOG_DIR.is_relative_to(PROJECT_ROOT)


def test_rotating_file_logging_redacts_sensitive_values(tmp_path):
    try:
        log_path = setup_logging(tmp_path)
        logger = logging.getLogger("step15.audit")
        logger.error(
            "login password=plain-secret; password_hash=hash-secret PWD=db-secret"
        )
        for handler in logging.getLogger().handlers:
            handler.flush()

        content = log_path.read_text(encoding="utf-8")
        assert "plain-secret" not in content
        assert "hash-secret" not in content
        assert "db-secret" not in content
        assert content.count("***") == 3
        assert log_path.parent == tmp_path
    finally:
        close_application_log_handlers()


def test_fatal_startup_is_logged_safely_and_shows_generic_message(
    monkeypatch, tmp_path
):
    shown = []
    monkeypatch.setattr(application_entry, "setup_logging", lambda: setup_logging(tmp_path))
    monkeypatch.setattr(
        application_entry,
        "main",
        lambda: (_ for _ in ()).throw(RuntimeError("password=do-not-expose")),
    )
    monkeypatch.setattr(
        application_entry.QMessageBox,
        "critical",
        lambda _parent, title, message: shown.append((title, message)),
    )

    try:
        assert application_entry.run() == 1
        for handler in logging.getLogger().handlers:
            handler.flush()
        content = (tmp_path / "app.log").read_text(encoding="utf-8")

        assert "do-not-expose" not in content
        assert "password=***" in content
        assert len(shown) == 1
        assert "do-not-expose" not in shown[0][1]
        assert "nhật ký" in shown[0][1]
    finally:
        close_application_log_handlers()


def test_database_connection_failure_is_normalized(monkeypatch):
    def fail_connect(*_args, **_kwargs):
        raise pyodbc.Error("raw driver connection detail")

    monkeypatch.setattr(pyodbc, "connect", fail_connect)

    with pytest.raises(DatabaseError) as exc_info:
        DatabaseManager("DRIVER={missing};SERVER=invalid").get_connection()

    message = str(exc_info.value)
    assert "SQL Server" in message
    assert "ODBC Driver 18" in message
    assert "raw driver" not in message


def test_excel_runtime_paths_are_caller_selected_and_not_cwd_dependent():
    sources = "\n".join(
        inspect.getsource(module)
        for module in (
            data_export_service,
            report_export_service,
            score_import_parser,
            score_import_template_service,
        )
    )

    assert "Path.cwd(" not in sources
    assert "getcwd(" not in sources
    assert "output_path" in sources
    assert "file_path" in sources


def test_runtime_and_development_dependencies_are_separated():
    root = PROJECT_ROOT
    runtime = (root / "requirements-runtime.txt").read_text(encoding="utf-8")
    development = (root / "requirements-dev.txt").read_text(encoding="utf-8")

    for dependency in (
        "bcrypt",
        "matplotlib",
        "openpyxl",
        "pyodbc",
        "PySide6",
        "python-dotenv",
    ):
        assert dependency in runtime
    assert "pytest" not in runtime.lower()
    assert "-r requirements-runtime.txt" in development
    assert "pytest" in development.lower()


def test_release_inputs_do_not_track_real_environment_or_runtime_logs():
    root = PROJECT_ROOT
    example = (root / ".env.example").read_text(encoding="utf-8")
    packaging = (root / "PACKAGING.md").read_text(encoding="utf-8")

    assert "DB_NAME=student_support_db" in example
    assert "DB_PASSWORD" not in example
    assert "onedir" in packaging.lower()
    assert "ODBC Driver 18" in packaging
