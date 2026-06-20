"""Session persistence with file-based JSON storage."""

from __future__ import annotations

import json
import os
import stat
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from platformdirs import user_state_dir

from tempmail_cli.exceptions import InvalidSessionError
from tempmail_cli.models import Account


_DEFAULT_DIR = Path(user_state_dir("tempmail-cli"))
_DEFAULT_FILE = _DEFAULT_DIR / "session.json"


def _session_path(name: str = "default") -> Path:
    if name == "default":
        return _DEFAULT_FILE
    return _DEFAULT_DIR / f"session_{name}.json"


def _serialize_account(account: Account) -> dict:
    data = asdict(account)
    data["created_at"] = account.created_at.isoformat()
    return data


def _deserialize_account(data: dict) -> Account:
    return Account(
        address=data["address"],
        password=data["password"],
        provider=data["provider"],
        token=data.get("token"),
        created_at=datetime.fromisoformat(data["created_at"]),
        raw=data.get("raw", {}),
    )


def save_session(account: Account, name: str = "default") -> Path:
    """Save account to disk with 600 permissions. Returns the file path."""
    path = _session_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Write to temp file first, then rename for atomicity
    tmp_path = path.with_suffix(".tmp")
    try:
        with open(tmp_path, "w") as f:
            json.dump(_serialize_account(account), f, indent=2)
        os.chmod(tmp_path, stat.S_IRUSR | stat.S_IWUSR)  # 0o600
        os.replace(tmp_path, path)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise

    return path


def load_session(name: str = "default") -> Account:
    """Load active session. Raises InvalidSessionError if not found."""
    path = _session_path(name)
    if not path.exists():
        raise InvalidSessionError(
            f"No active session '{name}'. Run `tempmail new` first.",
            hint="Run `tempmail new` to create a temporary mailbox.",
        )
    try:
        with open(path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        raise InvalidSessionError(f"Corrupt session file: {e}") from e
    return _deserialize_account(data)


def delete_session(name: str = "default") -> None:
    """Remove session file from disk."""
    path = _session_path(name)
    if path.exists():
        path.unlink()


def session_exists(name: str = "default") -> bool:
    """Check if a session file exists."""
    return _session_path(name).exists()
