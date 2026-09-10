# Chat Assistant Configuration

The assistant is disabled and offline by default. It always answers from the
approved static knowledge base; Gemini can only reformulate that context.
It is not configured as a general-purpose chatbot and does not use AI as a core
research model.

## Offline mode (default)

```dotenv
CHAT_ASSISTANT_ENABLED=false
CHAT_PROVIDER=offline
GEMINI_API_KEY=
```

Offline mode creates no Gemini client and makes no network request. Set
`CHAT_ASSISTANT_ENABLED=true` only when the desktop entry point should be shown.

## Optional Gemini mode

Copy `.env.example` to the application's normal environment-file location and
set values locally. Never commit the resulting `.env` file.

```dotenv
CHAT_ASSISTANT_ENABLED=true
CHAT_PROVIDER=gemini
GEMINI_API_KEY=<your key supplied outside source control>
GEMINI_MODEL=gemini-2.5-flash
GEMINI_TIMEOUT_SECONDS=15
GEMINI_MAX_RETRIES=1
```

Timeout is restricted to 1–60 seconds. Extra retries are restricted to 0–2.
Invalid values fall back to safe defaults; an unknown provider or missing key
selects offline mode without preventing application startup.

The key, prompts, conversation history, raw responses, and password material are
not logged. Provider errors are logged by category only. Authentication, quota,
timeout, network, malformed output, or unsafe output automatically falls back to
the matching static guidance. Requests without a knowledge match never call the
online provider.

## Security boundary

- The assistant has no database, repository, or business-service dependency.
- It cannot read real student data, run SQL, or change system state.
- Prompt-injection and credential requests are refused before provider calls.
- Conversation history is memory-only, bounded, and sanitized before online use.
- UI output is plain text and provider output is sanitized before display.

## Opt-in real-provider smoke

After configuring the local ignored `.env`, run:

```powershell
.\.venv\Scripts\python.exe scripts\smoke_gemini.py
```

The harness exits with `SKIPPED` and zero API calls unless a key exists and both
the assistant and `gemini` provider are explicitly enabled. It sends only curated
usage questions, never student or database data. Output contains pass/fail status,
source-independent case numbers, and the call count; it never prints the key,
full prompts, knowledge context, or full provider responses.
