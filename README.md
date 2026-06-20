# TempMail CLI

CLI tool for temporary email addresses with automatic verification code extraction.

Create disposable inboxes, receive emails, and extract confirmation codes — all from the terminal.

> **Privacy Warning:** Temporary email services are **public by design**. Do not use them for sensitive data. Emails received through these services can potentially be accessed by others. Never use temporary email for accounts containing real personal information, financial data, or anything you need to keep private.

## Installation

```bash
# Recommended: isolated install with pipx
pipx install tempmail-cli

# Or install with pip
pip install tempmail-cli
```

### Requirements

- Python 3.11+
- macOS, Linux, or Windows (WSL or native)

## Quick Start

```bash
# Create a temporary mailbox and wait for email
tempmail new
tempmail watch

# Wait for email from a specific sender, copy code to clipboard
tempmail watch --from "github.com" --copy

# Use Guerrilla Mail instead of mail.tm
tempmail new --provider guerrilla
tempmail watch
```

## Commands

| Command | Description |
|---------|-------------|
| `tempmail new` | Create a new temporary mailbox |
| `tempmail watch` | Wait for an incoming email and display it |
| `tempmail inbox` | List messages in the current mailbox |
| `tempmail read <id>` | Read a specific message by ID |
| `tempmail providers` | Show available mail providers and their status |
| `tempmail close` | Delete the temporary mailbox and clean up the session |

## Global Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--provider` | `mailtm` | Mail provider: `mailtm` or `guerrilla` |
| `--json` | off | Machine-readable JSON output |
| `--session-name` | `default` | Named session for parallel mailboxes |
| `--verbose` / `-v` | off | Verbose logging to stderr |
| `--debug` | off | Full debug output with traces |
| `--no-color` | off | Disable colored output (for CI) |
| `--version` / `-V` | | Show version and exit |

### Command-specific Flags

**`tempmail new`**

| Flag | Description |
|------|-------------|
| `--domain` | Specific domain to use |
| `--username` | Custom username (random if omitted) |

**`tempmail watch`**

| Flag | Default | Description |
|------|---------|-------------|
| `--interval` | 3 | Poll interval in seconds |
| `--timeout` | 120 | Max wait time in seconds |
| `--from` | | Filter by sender (substring match) |
| `--subject-contains` | | Filter by subject (substring match) |
| `--copy` | off | Copy verification code to clipboard |

**`tempmail inbox`**

| Flag | Default | Description |
|------|---------|-------------|
| `--limit` | 20 | Max messages to display |

**`tempmail read`**

| Flag | Description |
|------|-------------|
| `--copy` | Copy code/link to clipboard |
| `--raw` | Show raw HTML/text without parsing |

## Configuration

### Config File

Located at `~/.config/tempmail-cli/config.yaml`:

```yaml
default_provider: mailtm

providers:
  mailtm:
    base_url: "https://api.mail.tm"
    requests_per_second: 6
  guerrilla:
    base_url: "https://api.guerrillamail.com/ajax.php"
    requests_per_second: 0.5

defaults:
  interval: 3
  timeout: 120
  json_output: false
  copy_to_clipboard: false

output:
  color: true
```

### Environment Variables

Environment variables override config file values:

| Variable | Overrides |
|----------|-----------|
| `TEMPMAIL_PROVIDER` | `default_provider` |
| `TEMPMAIL_TIMEOUT` | `defaults.timeout` |
| `TEMPMAIL_INTERVAL` | `defaults.interval` |
| `TEMPMAIL_NO_COLOR` | `output.color = false` |
| `TEMPMAIL_LOG_FILE` | Log file path |

### Priority (lowest to highest)

Code defaults -> `config.yaml` -> Environment variables -> CLI flags

## Session Management

Sessions are stored in `~/.local/state/tempmail-cli/` with `600` permissions (owner-only). Named sessions allow running multiple mailboxes in parallel:

```bash
# Create two independent mailboxes
tempmail new --session-name work
tempmail new --session-name personal

# Watch each independently
tempmail watch --session-name work
tempmail watch --session-name personal
```

## Usage Examples

```bash
# Basic: create mailbox, wait for email, copy code
tempmail new
tempmail watch --copy

# Wait for GitHub confirmation with 5-minute timeout
tempmail watch --from "github.com" --timeout 300

# Use in scripts with JSON output
CODE=$(tempmail watch --json --timeout 60 | jq -r '.best_code')
echo "Code: $CODE"

# Check inbox
tempmail inbox

# Read a specific message
tempmail read <message-id>

# Clean up
tempmail close
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Business error (timeout, no session, message not found) |
| 2 | Configuration/argument error |
| 3 | Network error / provider unavailable |

## Providers

| Provider | Push Support | Rate Limit |
|----------|-------------|------------|
| mail.tm | Yes (not used in MVP) | 8 req/s |
| guerrilla | No | ~0.5 req/s (conservative) |

## License

MIT
