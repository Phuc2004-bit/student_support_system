# Student Support System 1.1.0

Release type: portable Windows 64-bit ONEDIR package.

## Highlights

- Modernized the application-wide user interface with a centralized dark theme.
- Modernized Login, MainWindow, sidebar, topbar, and Dashboard presentation.
- Refined Students, enrollment, history, and four-tab profile interfaces.
- Refined Scores and Assessments context, table, validation, and Excel interfaces.
- Refined the Support Workflow while preserving its existing state machine.
- Refined Reports, KPI, chart, filtering, table, and export presentation.
- Refined Catalog and System/account-management interfaces.
- Standardized dialog, input, table, status, empty-state, and chart styling.
- Added a secure deployment script for creating the first active ADMIN account.
- Protected initial-ADMIN bootstrap concurrency with a transaction-scoped SQL
  Server application lock.

## Compatibility and verification

- Existing UI → Service → Repository → Database architecture is unchanged.
- Existing ADMIN/TEACHER permissions and support business rules are unchanged.
- Pre-build regression baseline: **1196 passed, 0 failed, 0 errors**.
- Product: **Student Support System**; version: **1.1.0**.
- Executable: `StudentSupportSystem.exe`.

## Distribution notes

- SQL Server/SQL Server Express, ODBC Driver 18, the deployed database schema,
  and Windows Authentication access are external prerequisites.
- The initial ADMIN must be created by the deployer from a protected source
  checkout; the binary package does not include Python source or a registration UI.
- This is a portable ONEDIR ZIP without an installer, code signing, automatic
  updater, or custom application icon.
- No AI, mobile client, or cloud synchronization is included.
