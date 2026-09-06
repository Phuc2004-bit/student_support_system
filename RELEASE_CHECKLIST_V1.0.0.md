# Student Support System 1.0.0 — Release Checklist

| Check | Status | Evidence |
|---|---|---|
| Source tests | PASS | 1080 passed; 0 failed/errors |
| Clean ONEDIR build | PASS | `scripts/build_windows.ps1` |
| Executable exists | PASS | `StudentSupportSystem/StudentSupportSystem.exe` |
| Version/product metadata | PASS | 1.0.0 / Student Support System |
| PySide6 and qwindows | PASS | Packaged startup and dialogs |
| Matplotlib QtAgg and mpl-data | PASS | Dashboard and Reports rendered |
| pyodbc and ODBC 18 | PASS | `student_support_db_test` connection guard |
| bcrypt native runtime | PASS | Password change and re-login |
| openpyxl runtime | PASS | Template/import/export/read-back |
| python-dotenv runtime | PASS | `.env` resolved beside isolated EXE |
| Real `.env` absent | PASS | Recursive dist/ZIP audit |
| `.env.example` present | PASS | Production template in package |
| End-user documentation | PASS | `HUONG_DAN.txt` audited |
| No secrets/credentials | PASS | Recursive artifact and log audit |
| No tests/source/dev files | PASS | Recursive dist/ZIP audit |
| Packaged startup/login | PASS | LoginDialog and test ADMIN authentication |
| Navigation/charts/Excel | PASS | Frozen functional smoke |
| Logout/session safety | PASS | Logout/re-login and stale-window check |
| Log location/security | PASS | LocalAppData; no credentials/raw connection string |
| Database safety | PASS | Test DB only; T155 residual count 0 |
| ZIP generation/read-back | PASS | Automated release archive test |
| SHA-256 generation/verification | PASS | Sidecar checksum recalculated |
| Separate clean Windows machine/VM | PENDING | Isolated simulation only; required before broad deployment |
| Installer/code signing/custom icon | NOT INCLUDED | Outside V1.0 portable ZIP scope |

Build environment: Python 3.12.9, PyInstaller 6.22.2, PySide6 6.11.2,
pyodbc 5.3.0, openpyxl 3.1.5, matplotlib 3.11.1, bcrypt 5.0.0,
python-dotenv 1.2.3.
