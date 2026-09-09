# Student Support System 1.2.0

Usability and Windows installer release preparation.

## Highlights

- Added the official project-owned education/progress application icon.
- Applied one application identity to the executable, Login, and Sidebar.
- Added a per-user Inno Setup 6 installer configuration.
- Added Start Menu integration and an optional, unchecked Desktop shortcut.
- Validated clean install, same-version reinstall, uninstall, reinstall after
  uninstall, and installation to a path containing spaces and Unicode text.
- Added deployment-only utilities for securely creating the initial ADMIN and
  resetting an existing ADMIN password from a protected source checkout.
- Added non-blocking detection and documentation for external prerequisites.
- Preserved the existing PyInstaller ONEDIR runtime and all V1.1 business rules.

## Validation

- PyInstaller ONEDIR and Inno Setup installer runtime validated on Windows.
- ADMIN and TEACHER login, permissions, navigation, charts, and Excel workflows
  validated against the isolated test database where fixtures were required.
- Installer payload and runtime logs audited for credentials and temporary data.
- Automated suite: **1243 passed, 0 failed, 0 errors**.

## Deployment requirements

SQL Server or SQL Server Express, ODBC Driver 18, a deployed database schema,
Windows Authentication access, and an external `.env` remain prerequisites.
The installer does not download prerequisites, connect to a database, create an
ADMIN account, or include credentials. The initial ADMIN is created separately
from a protected source checkout. The installer is unsigned until an authentic
code-signing certificate is available, so Windows SmartScreen may warn.

V1.2 does not add a chatbot, AI feature, automatic updater, public registration,
or a signed/Trusted Publisher installer.
