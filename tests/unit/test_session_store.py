"""Tests for session store."""

import os
import pytest
from datetime import datetime, timezone

from tempmail_cli.models import Account
from tempmail_cli.session_store import save_session, load_session, delete_session, session_exists
from tempmail_cli.exceptions import InvalidSessionError


@pytest.fixture
def tmp_state_dir(monkeypatch, tmp_path):
    monkeypatch.setattr("tempmail_cli.session_store._DEFAULT_DIR", tmp_path)
    return tmp_path


def _make_account(address: str = "test@example.com") -> Account:
    return Account(
        address=address,
        password="pass",
        provider="mailtm",
        token="tok",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


class TestSessionStore:
    def test_save_and_load(self, tmp_state_dir):
        acc = _make_account()
        save_session(acc, "test")
        loaded = load_session("test")
        assert loaded.address == acc.address
        assert loaded.provider == acc.provider

    def test_file_permissions(self, tmp_state_dir):
        acc = _make_account()
        path = save_session(acc, "test")
        mode = os.stat(path).st_mode
        assert mode & 0o777 == 0o600

    def test_load_nonexistent_raises(self, tmp_state_dir):
        with pytest.raises(InvalidSessionError):
            load_session("nonexistent")

    def test_delete_session(self, tmp_state_dir):
        acc = _make_account()
        save_session(acc, "test")
        assert session_exists("test")
        delete_session("test")
        assert not session_exists("test")

    def test_corrupt_json_raises(self, tmp_state_dir):
        path = tmp_state_dir / "session.json"
        path.write_text("not json{{{")
        with pytest.raises(InvalidSessionError):
            load_session("default")

    def test_named_sessions(self, tmp_state_dir):
        acc1 = _make_account("a@test.com")
        acc2 = _make_account("b@test.com")
        save_session(acc1, "work")
        save_session(acc2, "personal")
        assert load_session("work").address == "a@test.com"
        assert load_session("personal").address == "b@test.com"
