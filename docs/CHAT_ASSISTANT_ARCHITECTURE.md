# Chat Assistant Architecture — V1.3 / Steps 19.1–19.4

## Scope and boundary

Chat Assistant is a Vietnamese, read-only usage guide. It answers from approved
static application knowledge only. It cannot query the database, inspect real
student data, execute SQL, expose credentials, or mutate application state.
It is not a general-purpose chatbot or a core research model; no-match and
out-of-scope questions are refused or handled by deterministic offline guidance.
Step 19.4 optionally reformulates retrieved static guidance with Gemini, without
adding database access or business actions.

```text
MainWindow feature-flag entry point
    -> ChatAssistantDialog
    -> ChatAssistantWidget
    -> ChatAssistantService
       -> TopicGuard
       -> KnowledgeBase
       -> Provider factory
          -> OfflineProvider
          -> GeminiProvider (optional, static context only)
             -> failure/unsafe response -> OfflineProvider
```

The chat widget calls `ChatAssistantService.ask()` only. A `QThreadPool` worker
keeps this call off the UI thread and is ready for a future provider with network
latency. The worker has no database or business dependency.

The `assistant` package and chat UI must not import repositories, database modules, or the
Student, Score, Support, User, and Report business services. Conversation history
is memory-only and limited before it reaches a provider.

## Approved knowledge sources

The default allowlist is intentionally explicit:

- `assistant/knowledge/faq_vi.json`
- `assistant/knowledge/workflows_vi.json`
- `HUONG_DAN.txt`
- `RELEASE_NOTES_V1.2.0.md`
- `installer/PREREQUISITES_V1.2.txt`

KnowledgeBase never walks or indexes the project directory. Structured FAQ and
workflow entries are the retrieval source. Approved public documents remain
available as bounded static context and for future curated ingestion.

## FAQ schema and validation

Each JSON entry has `id`, `category`, `question`, `aliases`, `answer`, `keywords`,
and `screen`. Loading validates required fields, non-empty text, allowed category,
globally unique IDs, aliases that do not collide after normalization, UTF-8 JSON,
and forbidden secret/connection/hash patterns. Invalid knowledge raises
`KnowledgeBaseError`; the service converts runtime knowledge failures to a safe
response without exposing the cause.

See `CHAT_ASSISTANT_FAQ_GUIDE.md` before changing the knowledge files.

## Deterministic offline retrieval

Retrieval has no ML or vector dependency. Ranking order is:

1. normalized exact question;
2. normalized exact alias;
3. keyword overlap and safe phrase match;
4. generic token overlap.

Vietnamese normalization uses case folding, removes combining accents, maps `đ`
to `d`, removes punctuation, and collapses whitespace. Stored answers are never
normalized or rewritten.

Matches below the confidence floor return the explicit offline fallback rather
than the nearest entry. Equal top scores return a clarification prompt instead of
guessing. A confident query returns only the top entry.

## Source attribution

Structured sources are stable logical labels such as `faq:login_001` and
`workflow:support_review`. Clarification and no-match responses use
`offline:clarify` and `offline:fallback`. Absolute filesystem paths are never
returned to callers.

## Safety policy

TopicGuard allows guidance questions but blocks requests to read real student
data or credentials, execute SQL, or change scores, support state, users, or
rules. The knowledge explains supported screens and workflows only. Provider
responses are checked for secret, connection-string, hash, and internal-prompt
patterns before being returned.

## Provider safety and fallback

`CHAT_PROVIDER=offline` is the default and constructs no Gemini client. With an
explicit `gemini` provider and non-empty key, the official Google Gen AI SDK is
configured with a finite timeout and bounded transient retries. The provider is
given only the retrieved static context, the current question, and sanitized,
bounded in-memory history. It never receives repositories, database connections,
student records, credentials, filesystem paths, or business services.

Topic and prompt-injection checks run before retrieval/provider invocation. No
knowledge match means Gemini is not called. Authentication, quota, timeout,
network, malformed-response, and sanitizer failures return deterministic offline
guidance while preserving the static knowledge source. Logs contain only failure
categories, never prompts, API keys, history, or raw provider responses.

## Desktop UI and configuration

`CHAT_ASSISTANT_ENABLED=false` remains the safe default. When disabled, MainWindow
does not display the Topbar entry or construct the assistant service/dialog. When
enabled, the Topbar button opens a reusable non-modal dialog without adding or
changing a navigation page. The badge reports `Offline`, `Trực tuyến`, or
`Đang dùng chế độ offline` through the service's provider-neutral interface.

The dialog uses plain-text message bubbles, memory-only history limited to 12
messages, quick guidance questions, Enter-to-send, Shift+Enter for a newline,
automatic scrolling, a clear-memory action, and friendly source labels. Internal
source IDs and raw HTML/Markdown are not rendered. Errors are normalized to the
safe assistant message.

Sizing is bounded for 1280×720, 1366×768, 1920×1080, and 125% logical scaling.
Colors and component states come from `ui/theme.py`.

Configuration instructions are in `CHAT_ASSISTANT_CONFIGURATION.md`.
