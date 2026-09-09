# Student Support System 1.1.0 — Release Checklist

| Check | Status | Evidence |
|---|---|---|
| Source tests | PASS | 1200 pre-artifact tests plus 3 final-artifact tests |
| Clean ONEDIR build | PASS | `scripts/build_windows.ps1` |
| Runtime prerequisites documented | PASS | `HUONG_DAN.txt` and `PACKAGING.md` |
| Packaged functional smoke | PASS | Guarded `student_support_db_test` smoke and cleanup |
| ADMIN navigation and core flows | PASS | Packaged functional smoke |
| TEACHER permission/navigation | PASS | Packaged functional smoke |
| bcrypt authentication/password change | PASS | Packaged functional smoke |
| Initial ADMIN bootstrap regression | PASS | Source tests; SQL Server application lock |
| ZIP generation and read-back | PASS | `scripts/finalize_release.ps1` and ZIP test |
| Checksum (SHA-256) generation and verification | PASS | `.sha256` sidecar verified against ZIP bytes |
| Clean Unicode/space-path extraction | PASS | Sanitized T172 smoke, test DB only |
| Real `.env` absent | PASS | Recursive dist/ZIP audit; only `.env.example` included |
| Source/tests/dev artifacts absent | PASS | Recursive dist/ZIP audit |
| Secrets absent from package and logs | PASS | No credentials or runtime logs packaged |
| Git tag | PENDING | Deliberately not performed in Step 17.2 |
| GitHub Release | PENDING | Deliberately not performed in Step 17.2 |
| Installer/code signing/custom icon | NOT INCLUDED | Outside portable ZIP scope |

Build environment target: Python 3.12.9, PyInstaller 6.22.2, PySide6 6.11.2,
pyodbc 5.3.0, openpyxl 3.1.5, matplotlib 3.11.1, bcrypt 5.0.0,
python-dotenv 1.2.3.
