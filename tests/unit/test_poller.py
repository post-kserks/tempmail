"""Tests for the poller."""

import time
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from tempmail_cli.models import Account, Message
from tempmail_cli.poller import Poller
from tempmail_cli.providers.base import MailProvider
from tempmail_cli.exceptions import TimeoutWaitingForMailError


class FakeProvider(MailProvider):
    name = "fake"

    def __init__(self, messages: list[Message] | None = None) -> None:
        self._messages = messages or []
        self._call_count = 0

    def list_domains(self) -> list[str]:
        return ["fake.com"]

    def create_account(self, domain=None, username=None) -> Account:
        return Account(
            address="test@fake.com",
            password="pass",
            provider="fake",
            token=None,
            created_at=datetime.now(timezone.utc),
        )

    def list_messages(self, account, since_id=None) -> list[Message]:
        self._call_count += 1
        if self._call_count > 1 and self._messages:
            return self._messages
        return []

    def get_message(self, account, message_id) -> Message:
        for m in self._messages:
            if m.id == message_id:
                return m
        return self._messages[0] if self._messages else Message(
            id="1",
            from_address="test@example.com",
            from_name=None,
            subject="Test",
            received_at=datetime.now(timezone.utc),
            text_body="test",
            html_body=None,
            seen=False,
        )

    def delete_account(self, account) -> None:
        pass


def _make_account() -> Account:
    return Account(
        address="test@fake.com",
        password="pass",
        provider="fake",
        token=None,
        created_at=datetime.now(timezone.utc),
    )


_msg_counter = 0


def _make_message(subject: str = "Test", from_addr: str = "test@example.com") -> Message:
    global _msg_counter
    _msg_counter += 1
    return Message(
        id=str(_msg_counter),
        from_address=from_addr,
        from_name=None,
        subject=subject,
        received_at=datetime.now(timezone.utc),
        text_body="test body",
        html_body=None,
        seen=False,
    )


@pytest.fixture(autouse=True)
def _reset_counter():
    global _msg_counter
    _msg_counter = 0
    yield


class TestPoller:
    def test_receives_message(self):
        msg = _make_message()
        provider = FakeProvider(messages=[msg])
        poller = Poller(provider, _make_account(), interval=0.1, timeout=5.0)

        result = poller.wait_for_message()
        assert result.id == "1"
        assert result.subject == "Test"

    def test_timeout_raises(self):
        provider = FakeProvider(messages=[])
        poller = Poller(provider, _make_account(), interval=0.1, timeout=0.3)

        with pytest.raises(TimeoutWaitingForMailError):
            poller.wait_for_message()

    def test_filter_by_sender(self):
        msg1 = _make_message(from_addr="spam@evil.com")
        msg2 = _make_message(from_addr="github@github.com")
        provider = FakeProvider(messages=[msg1, msg2])
        poller = Poller(provider, _make_account(), interval=0.1, timeout=5.0)

        result = poller.wait_for_message(from_contains="github")
        assert result.from_address == "github@github.com"

    def test_filter_by_subject(self):
        msg1 = _make_message(subject="Spam offer")
        msg2 = _make_message(subject="Confirm your email")
        provider = FakeProvider(messages=[msg1, msg2])
        poller = Poller(provider, _make_account(), interval=0.1, timeout=5.0)

        result = poller.wait_for_message(subject_contains="Confirm")
        assert "Confirm" in result.subject
