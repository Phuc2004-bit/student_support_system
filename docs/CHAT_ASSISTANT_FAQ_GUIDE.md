# Safe FAQ maintenance guide

Add knowledge only to the two allowlisted UTF-8 JSON files under
`assistant/knowledge/`. Do not point the loader at a directory.

Every entry must provide:

- a globally unique, stable `id`;
- one allowed `category`;
- a concise Vietnamese `question` and non-empty `answer`;
- distinct `aliases` that do not duplicate another entry after accent/case
  normalization;
- focused one-word `keywords` for deterministic retrieval;
- the real `screen` name, without inventing controls.

Answers may explain navigation and existing rules. They must not contain real
credentials, secrets, connection strings, password hashes, student data, SQL to
execute, or instructions that bypass operating-system security. Do not insert a
fixed support threshold: always say that the threshold comes from the configured
support rule.

After editing, run the Step 19.2 tests. They validate schema, sources, security,
retrieval behavior, workflow wording, and the assistant architecture boundary.
