# Student Support System 1.3.0

Secure, read-only Chat Assistant release.

## Highlights

- Added a PySide6 Chat Assistant UI for questions about using the application.
- Added an approved static Knowledge Base with 27 FAQ entries and 4 workflow entries.
- Added a fully offline mode that requires no external AI service or API key.
- Added an optional Gemini provider using the pinned `google-genai==2.22.0` SDK.
- Grounded provider responses in approved knowledge instead of general-purpose chat.
- Added prompt-injection, credential-request, SQL, mutation, and real-data defenses.
- Added bounded timeout/retry handling with deterministic offline fallback.
- Added secret, prompt, conversation-history, and provider-output log redaction.
- Validated the assistant and knowledge resources in the packaged PyInstaller runtime.

## Security boundary

The Chat Assistant does not access the database, repositories, student data, or
business mutation services. It cannot modify application data or run SQL. It is
not a general-purpose chatbot and is not the AI core of the research model.
Conversation history is bounded and kept in memory only.

Gemini integration is optional. The release defaults to the disabled offline
configuration and never bundles a Gemini API key. A deployer may opt in using an
external `.env` file as documented in `docs/CHAT_ASSISTANT_CONFIGURATION.md`.

## Validation

- Automated suite: **1400 passed, 1 skipped, 0 failed, 0 errors**.
- PyInstaller ONEDIR smoke covered disabled, offline, no-key fallback, knowledge,
  safety, ADMIN/TEACHER permissions, core workflows, Excel, and Unicode relocation.
- The one skipped check is the opt-in real-Gemini smoke. No real Gemini API call
  was made, and this is not claimed as a passing live-provider validation.

## Deployment requirements

SQL Server or SQL Server Express, ODBC Driver 18, a deployed database schema,
Windows Authentication access, and an external `.env` remain prerequisites.
The unsigned installer does not download prerequisites, create a database, create
accounts, or include credentials.
