# Architecture

## Overview

```
                          ┌──────────────────────┐
                          │       CLI Layer        │
                          │   (typer commands)      │
                          │  new / watch / inbox /  │
                          │  read / providers /     │
                          │  close                  │
                          └───────────┬────────────┘
                                      │
                  ┌───────────────────┼───────────────────┐
                  │                   │                   │
          ┌───────▼───────┐  ┌──────▼───────┐  ┌────────▼────────┐
          │  SessionStore   │  │   Poller      │  │  OutputFormatter │
          │ (~/.local/state)│  │  (blocking)   │  │ (rich / json)    │
          └───────┬────────┘  └──────┬────────┘  └─────────────────┘
                  │                   │
          ┌───────▼───────────────────▼────────┐
          │         ProviderManager             │
          │  selection, health-check, fallback   │
          └───────┬───────────────────┬────────┘
                  │                   │
        ┌─────────▼─────────┐ ┌──────▼──────────────┐
        │  MailTmProvider    │ │ GuerrillaMailProvider │
        │ (MailProvider ABC) │ │ (MailProvider ABC)   │
        └─────────┬─────────┘ └──────┬──────────────┘
                  │                   │
          ┌───────▼───────────────────▼───────┐
          │          HTTP Client               │
          │     (requests.Session + retry)     │
          └───────────────────────────────────────┘

                  ┌─────────────────────────┐
                  │      MessageParser       │
                  │  (BeautifulSoup + regex) │
                  │  extracts codes & links  │
                  └─────────────────────────┘
```

## Key Principles

### Provider Abstraction

All mail service integrations implement the `MailProvider` abstract base class defined in `providers/base.py`. The CLI layer and business logic never call HTTP APIs directly — they go through this interface. Adding a new provider means implementing one class without touching the rest of the application.

### I/O Separation

The message parser (`parser.py`) and data models (`models.py`) have no knowledge of HTTP. They operate on normalized `Message` objects and can be tested on fixtures without network calls. Output formatting (`output.py`) is similarly isolated — the same data renders as rich text or JSON depending on the `--json` flag.

### Fail-soft

When a provider is unavailable, the system suggests an alternative (`--provider guerrilla`) but never switches automatically without user consent. Provider health is checked before each operation. Retry logic handles transient failures (5xx, timeouts) with exponential backoff before surfacing errors.

### Security

- Account passwords are generated with `secrets.token_urlsafe(16)` and never displayed in normal output.
- Session files are created with `0o600` permissions (owner-only read/write).
- Debug logs mask sensitive fields (`Authorization: Bearer ***`).
- No telemetry or "phone home" calls — the tool only contacts the selected mail provider.

## Components

### CLI Layer (`cli.py`)

Typer application that registers all commands. Handles argument parsing, logging setup, and delegates to business logic. Each command follows the same pattern: load session, resolve provider, perform operation, format output.

### Models (`models.py`)

Immutable frozen dataclasses:

- `Account` — temporary email address, credentials, provider name, session token
- `Message` — email with sender, subject, text/HTML bodies, timestamp
- `ParsedContent` — extraction results: candidate codes, links, best guesses

### Provider Manager (`provider_manager.py`)

Maintains a registry of available providers. `resolve()` instantiates the requested provider, runs a health check, and suggests alternatives if unavailable. No network logic — only routing.

### Providers (`providers/`)

Each provider implements the `MailProvider` ABC:

| Provider | API | Auth | Push |
|----------|-----|------|------|
| `MailTmProvider` (`mailtm.py`) | REST (`api.mail.tm`) | JWT bearer token | Yes (unused) |
| `GuerrillaMailProvider` (`guerrilla.py`) | JSON API (`api.guerrillamail.com`) | `sid_token` session | No |

Providers translate their service-specific responses into the normalized `Account` and `Message` models. They also handle rate limiting via an internal token-bucket rate limiter.

### Poller (`poller.py`)

Blocking loop that polls the provider for new messages. Supports:

- Configurable poll interval and timeout
- Filtering by sender address and subject
- Graceful `SIGINT`/`SIGTERM` handling (clean exit instead of traceback)

### Message Parser (`parser.py`)

Extracts verification codes and confirmation links from email content:

1. **Code detection** — regex patterns search for 4-10 character codes near context markers (code, OTP, verification, confirm, etc.). Candidates are scored by proximity to markers and length.
2. **Link detection** — extracts all `http`/`https` hrefs from HTML. Links are scored by keywords (confirm, verify, activate, etc.). Service links (unsubscribe, privacy) are excluded from "best link" selection.

### Session Store (`session_store.py`)

Persists active mailbox state to disk as JSON. Uses atomic writes (write to `.tmp`, then `os.replace`) and sets `0o600` permissions. Named sessions (`session_<name>.json`) allow parallel mailbox management.

### Output Formatter (`output.py`)

Dual-mode renderer:

- **Rich text** — colored panels, tables, and spinners via the `rich` library
- **JSON** — machine-readable output via `json.dumps` with datetime serialization

### Configuration (`config.py`)

Layered config with four priority levels (lowest to highest):

1. Code defaults
2. `~/.config/tempmail-cli/config.yaml`
3. Environment variables (`TEMPMAIL_*`)
4. CLI flags

### Clipboard (`clipboard.py`)

Wrapper around `pyperclip` with graceful fallback — logs a warning and returns `False` if no clipboard mechanism is available (headless environments, SSH sessions).

## Request Flow: `tempmail watch`

```
1. Load active session from disk (or error if none exists)
2. Resolve provider from session's provider name (with health check)
3. Create Poller with interval/timeout settings
4. Polling loop:
   a. provider.list_messages(since=last_seen_id)
   b. If empty → sleep(interval), repeat until timeout
   c. If match found → provider.get_message(id) → full Message
5. parser.parse_message(message) → ParsedContent
6. OutputFormatter renders result (rich text or JSON)
7. (optional) copy best_code or best_link to clipboard
```

## Error Hierarchy

```
TempMailError (base)
├── ProviderUnavailableError    — provider unreachable after retries
├── RateLimitedError            — provider returned 429
├── AuthError                   — authentication failed
├── MessageNotFoundError        — specific message not found
├── TimeoutWaitingForMailError  — watch timeout expired
├── InvalidSessionError         — no active session for command
└── ConfigError                 — invalid configuration file
```

Every exception carries a human-readable message and an optional `hint` field suggesting corrective action (e.g., "Try --provider guerrilla").
