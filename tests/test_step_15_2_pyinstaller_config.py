from __future__ import annotations

from importlib.metadata import version
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parent.parent


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_pyinstaller_is_pinned_as_development_dependency_only():
    assert version("PyInstaller") == "6.22.2"
    assert "PyInstaller==6.22.2" in read("requirements-dev.txt")
    assert "pyinstaller" not in read("requirements-runtime.txt").lower()


def test_spec_uses_main_entry_and_maintainable_onedir_structure():
    spec = read("StudentSupportSystem.spec")

    assert '["main.py"]' in spec
    assert all(token in spec for token in ("Analysis(", "PYZ(", "EXE(", "COLLECT("))
    assert "exclude_binaries=True" in spec
    assert 'name="StudentSupportSystem"' in spec
    assert "console=False" in spec
    assert "onefile" not in spec.lower()


def test_spec_has_no_developer_absolute_path_or_real_environment_file():
    spec = read("StudentSupportSystem.spec")

    assert not re.search(r"[A-Za-z]:[\\/]", spec)
    assert ".env" not in spec
    assert "tests" not in spec
    assert 'excludes=["pytest"]' in spec


def test_spec_uses_hooks_before_adding_speculative_collection_rules():
    spec = read("StudentSupportSystem.spec")

    assert "hiddenimports=[]" in spec
    assert "binaries=[]" in spec
    assert '("assets/app_icon.png", "assets")' in spec
    assert '("assets/app_icon.ico", "assets")' in spec
    assert "collect_all" not in spec
    assert "collect_submodules" not in spec


def test_windows_version_metadata_uses_release_name_without_fake_company():
    metadata = read("build_config/windows_version_info.txt")

    assert "Student Support System" in metadata
    assert "StudentSupportSystem.exe" in metadata
    assert "1.2.0" in metadata
    assert "StringStruct('CompanyName', '')" in metadata


def test_build_script_is_scoped_and_invokes_the_committed_spec():
    script = read("scripts/build_windows.ps1")

    assert "Assert-ProjectChildPath" in script
    assert "Remove-Item -LiteralPath $Target -Recurse -Force" in script
    assert "-m PyInstaller --noconfirm --clean $Spec" in script
    assert "StudentSupportSystem.spec" in script
    assert "StudentSupportSystem.exe" in script
    assert "qwindows.dll" in script
    assert "pyodbc*.pyd" in script
    assert "_bcrypt.pyd" in script
    assert "matplotlibrc" in script


def test_build_script_copies_only_environment_template_and_guide():
    script = read("scripts/build_windows.ps1")

    assert 'Join-Path $ProjectRoot ".env.example"' in script
    assert 'Join-Path $ProjectRoot "HUONG_DAN.txt"' in script
    assert 'Join-Path $ProjectRoot ".env"' not in script


def test_release_guide_documents_external_runtime_prerequisites():
    guide = read("HUONG_DAN.txt")

    assert "STUDENT SUPPORT SYSTEM V1.2" in guide
    assert "ODBC Driver 18 for SQL Server" in guide
    assert "SQL Server" in guide
    assert "Windows user" in guide
    assert ".env.example" in guide and ".env" in guide
    assert "%LOCALAPPDATA%\\StudentSupportSystem\\logs\\app.log" in guide


def test_gitignore_keeps_artifacts_out_but_allows_committed_spec():
    gitignore = read(".gitignore")

    assert "build/" in gitignore
    assert "dist/" in gitignore
    assert "*.spec" not in gitignore


def test_packaging_documentation_records_build_and_known_caveats():
    document = read("PACKAGING.md")

    assert "build_windows.ps1" in document
    assert "PyInstaller 6.22.2" in document
    assert "ONEDIR" in document
    assert "qwindows.dll" in document
    assert "ODBC" in document
    assert "real `.env`" in document
    assert "seven-second startup smoke" in document
    assert "No hidden imports" in document
