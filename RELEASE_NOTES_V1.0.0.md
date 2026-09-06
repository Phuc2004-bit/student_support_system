# Student Support System 1.0.0

Release type: portable Windows 64-bit ONEDIR package.

## Included modules

- Student records, enrollment, transfers, enrollment history, and four-tab profiles.
- Assessments, manual scores, score history, validation, and duplicate protection.
- Score-driven support detection and the complete intervention review workflow.
- Dashboard, support reports, charts, filters, and Excel exports.
- School-year, grade, class, subject, assessment, and support-rule catalogs.
- ADMIN/TEACHER permissions, account management, profiles, and password changes.
- Transactional Excel score import plus Students, Scores, Support, and Reports exports.

## Runtime and verification

- Product: **Student Support System**; version: **1.0.0**.
- Executable: `StudentSupportSystem.exe`.
- Database: an existing Microsoft SQL Server/SQL Server Express database accessed
  through Windows Authentication and Microsoft ODBC Driver 18 for SQL Server.
- Source and packaging suite: **1080 passed, 0 failed, 0 errors**.
- Packaged runtime and isolated-distribution simulation passed on Windows 11 with
  no source-tree, `.venv`, Python interpreter, or launch-working-directory dependency.

## Known limitations

- SQL Server/SQL Server Express, ODBC Driver 18, the deployed database schema, and
  suitable Windows database permissions must be provided separately.
- This release is a portable ONEDIR ZIP; it has no installer, code signing, updater,
  or official custom Windows icon.
- It has not been tested on a separate clean physical Windows machine or VM.
  Additional clean-machine testing is recommended before broad deployment.
- V1.0 does not include chatbot or AI functionality.
