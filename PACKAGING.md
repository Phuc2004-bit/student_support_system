# Windows packaging audit (Step 15.1)

## Release recommendation

Use a PyInstaller **onedir** build for V1.0. PySide6, matplotlib, pyodbc and
bcrypt include native components; onedir gives predictable startup, makes Qt
plugins and DLLs easier to inspect, and avoids onefile temporary extraction.

Proposed release layout:

```text
dist/
  StudentSupportSystem/
    StudentSupportSystem.exe
    .env.example
    HUONG_DAN.txt
```

Product name: `Student Support System`; version: `1.0.0`; executable:
`StudentSupportSystem.exe`. The project currently has no `.ico` file, so a real
Windows application icon remains an input for a later packaging step.

## Runtime configuration and writable files

The production entry point is `main.py`, which composes dependencies through
`bootstrap.build_app_context()`, opens the login dialog, then MainWindow.

Runtime `.env` is external and is read beside the executable in a frozen build.
Do not bundle the real `.env`; ship `.env.example` as the configuration template.
The production default database is `student_support_db`, never the test database.
Logs are written to `%LOCALAPPDATA%/StudentSupportSystem/logs/app.log` with
rotation. Password-like fields are redacted by the logging formatter.

There are currently no icons, images, stylesheets, fonts or workbook templates to
bundle. Excel templates are generated programmatically and import/export paths
come from the file dialog. `config.paths.resource_path()` is available if a
read-only resource is added later.

## External prerequisites

- 64-bit Windows compatible with Python 3.12 and the packaged Qt runtime.
- Microsoft SQL Server or SQL Server Express and an existing production database.
- Windows Authentication access for the signed-in Windows user.
- Microsoft ODBC Driver 18 for SQL Server installed on the target machine.

SQL Server and the ODBC driver remain external prerequisites; neither should be
bundled into the application. pyodbc and bcrypt native extensions, Qt platform
plugins (especially `platforms/qwindows.dll`), and matplotlib data/backend hooks
must be verified in Step 15.2. The current charts use QtAgg through PySide6.

## Build inputs and exclusions

Use `requirements-runtime.txt` for runtime dependencies and
`requirements-dev.txt` for tests. `requirements.txt` remains the full pinned
development environment snapshot.

Exclude `tests/`, `.git/`, `.venv/`, `.pytest_cache/`, `__pycache__/`, `logs/`,
coverage output, test database scripts and temporary Excel files. Do not include
real credentials or test accounts.

## Validation checklist for later steps

1. Launch from source.
2. Build onedir with PyInstaller.
3. Launch `StudentSupportSystem.exe` without a console.
4. Confirm log creation under `%LOCALAPPDATA%`.
5. Verify friendly behavior for missing ODBC driver and unavailable SQL Server.
6. Connect to the configured production database and log in.
7. Exercise all navigation and charts.
8. Import and export Excel workbooks to a user-selected directory.
9. Log out and log in again.
10. Repeat smoke tests on a clean Windows machine with only documented external
    prerequisites installed.

Step 15.1 does not create a PyInstaller spec, executable, installer, or final
release directory.
