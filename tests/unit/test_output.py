"""Tests for output formatting."""

import json
from datetime import datetime, timezone
from io import StringIO

import pytest

from tempmail_cli.models import Account, Message, ParsedContent
from tempmail_cli.output import OutputFormatter


@pytest.fixture
def account():
    return Account(
        address="test@example.com",
        password="secret",
        provider="mailtm",
        token="tok",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        raw={},
    )


@pytest.fixture
def message():
    return Message(
        id="msg-1",
        from_address="sender@example.com",
        from_name="Sender",
        subject="Your code is 123456",
        received_at=datetime(2026, 6, 21, 12, 0, 0, tzinfo=timezone.utc),
        text_body="Your code: 123456",
        html_body=None,
        seen=False,
    )


@pytest.fixture
def parsed_with_code():
    return ParsedContent(
        codes=["123456"],
        links=[],
        best_code="123456",
        best_link=None,
    )


@pytest.fixture
def parsed_with_link():
    return ParsedContent(
        codes=[],
        links=["https://example.com/verify?token=abc"],
        best_code=None,
        best_link="https://example.com/verify?token=abc",
    )


@pytest.fixture
def parsed_with_both():
    return ParsedContent(
        codes=["123456", "789012"],
        links=["https://example.com/a", "https://example.com/b"],
        best_code="123456",
        best_link="https://example.com/a",
    )


@pytest.fixture
def parsed_empty():
    return ParsedContent()


class TestOutputFormatterJson:
    def test_print_account_created_json(self, account, capsys):
        fmt = OutputFormatter(json_mode=True, color=False)
        fmt.print_account_created(account, "/tmp/session.json")
        output = capsys.readouterr().out.strip()
        data = json.loads(output)
        assert data["address"] == "test@example.com"
        assert data["provider"] == "mailtm"

    def test_print_message_with_code_json(self, message, parsed_with_code, capsys):
        fmt = OutputFormatter(json_mode=True, color=False)
        fmt.print_message(message, parsed_with_code)
        data = json.loads(capsys.readouterr().out.strip())
        assert data["from"] == "sender@example.com"
        assert data["subject"] == "Your code is 123456"
        assert data["best_code"] == "123456"
        assert data["best_link"] is None

    def test_print_message_with_link_json(self, message, parsed_with_link, capsys):
        fmt = OutputFormatter(json_mode=True, color=False)
        fmt.print_message(message, parsed_with_link)
        data = json.loads(capsys.readouterr().out.strip())
        assert data["best_code"] is None
        assert data["best_link"] == "https://example.com/verify?token=abc"

    def test_print_message_empty_json(self, message, parsed_empty, capsys):
        fmt = OutputFormatter(json_mode=True, color=False)
        fmt.print_message(message, parsed_empty)
        data = json.loads(capsys.readouterr().out.strip())
        assert data["best_code"] is None
        assert data["best_link"] is None
        assert data["all_codes"] == []
        assert data["all_links"] == []

    def test_print_inbox_empty_json(self, capsys):
        fmt = OutputFormatter(json_mode=True, color=False)
        fmt.print_inbox([])
        data = json.loads(capsys.readouterr().out.strip())
        assert data == []

    def test_print_inbox_single_json(self, message, capsys):
        fmt = OutputFormatter(json_mode=True, color=False)
        fmt.print_inbox([message])
        data = json.loads(capsys.readouterr().out.strip())
        assert len(data) == 1
        assert data[0]["id"] == "msg-1"
        assert data[0]["from"] == "sender@example.com"
        assert data[0]["seen"] is False

    def test_print_providers_json(self, capsys):
        providers = {
            "mailtm": {"online": True, "supports_push": True},
            "guerrilla": {"online": False, "supports_push": False},
        }
        fmt = OutputFormatter(json_mode=True, color=False)
        fmt.print_providers(providers, "mailtm")
        data = json.loads(capsys.readouterr().out.strip())
        assert data["mailtm"]["online"] is True

    def test_print_error_json(self, capsys):
        fmt = OutputFormatter(json_mode=True, color=False)
        fmt.print_error("Something went wrong")
        data = json.loads(capsys.readouterr().out.strip())
        assert data["error"] == "Something went wrong"
        assert "hint" not in data

    def test_print_error_with_hint_json(self, capsys):
        fmt = OutputFormatter(json_mode=True, color=False)
        fmt.print_error("Failed", hint="Check your connection")
        data = json.loads(capsys.readouterr().out.strip())
        assert data["error"] == "Failed"
        assert data["hint"] == "Check your connection"

    def test_print_info_json(self, capsys):
        fmt = OutputFormatter(json_mode=True, color=False)
        fmt.print_info("Some info")
        data = json.loads(capsys.readouterr().out.strip())
        assert data["info"] == "Some info"

    def test_print_clipboard_copy_json(self, capsys):
        fmt = OutputFormatter(json_mode=True, color=False)
        fmt.print_clipboard_copy("123456")
        data = json.loads(capsys.readouterr().out.strip())
        assert data["copied"] == "123456"


class TestOutputFormatterRich:
    def test_print_account_created_rich(self, account, capsys):
        fmt = OutputFormatter(json_mode=False, color=False)
        fmt.print_account_created(account, "/tmp/session.json")
        output = capsys.readouterr().out
        assert "test@example.com" in output

    def test_print_message_with_code_rich(self, message, parsed_with_code, capsys):
        fmt = OutputFormatter(json_mode=False, color=False)
        fmt.print_message(message, parsed_with_code)
        output = capsys.readouterr().out
        assert "123456" in output

    def test_print_message_with_link_rich(self, message, parsed_with_link, capsys):
        fmt = OutputFormatter(json_mode=False, color=False)
        fmt.print_message(message, parsed_with_link)
        output = capsys.readouterr().out
        assert "https://example.com/verify?token=abc" in output

    def test_print_message_empty_rich(self, message, parsed_empty, capsys):
        fmt = OutputFormatter(json_mode=False, color=False)
        fmt.print_message(message, parsed_empty)
        output = capsys.readouterr().out
        assert "sender@example.com" in output

    def test_print_message_multiple_codes_rich(self, message, parsed_with_both, capsys):
        fmt = OutputFormatter(json_mode=False, color=False)
        fmt.print_message(message, parsed_with_both)
        output = capsys.readouterr().out
        assert "789012" in output
        assert "https://example.com/b" in output

    def test_print_inbox_empty_rich(self, capsys):
        fmt = OutputFormatter(json_mode=False, color=False)
        fmt.print_inbox([])
        output = capsys.readouterr().out
        assert "Inbox" in output

    def test_print_inbox_single_rich(self, message, capsys):
        fmt = OutputFormatter(json_mode=False, color=False)
        fmt.print_inbox([message])
        output = capsys.readouterr().out
        assert "msg-1" in output
        assert "sender@example.com" in output

    def test_print_providers_rich(self, capsys):
        providers = {
            "mailtm": {"online": True, "supports_push": True},
        }
        fmt = OutputFormatter(json_mode=False, color=False)
        fmt.print_providers(providers, "mailtm")
        output = capsys.readouterr().out
        assert "mailtm" in output

    def test_print_error_rich(self, capsys):
        fmt = OutputFormatter(json_mode=False, color=False)
        fmt.print_error("Something went wrong")
        output = capsys.readouterr().out
        assert "Something went wrong" in output

    def test_print_error_with_hint_rich(self, capsys):
        fmt = OutputFormatter(json_mode=False, color=False)
        fmt.print_error("Failed", hint="Check connection")
        output = capsys.readouterr().out
        assert "Failed" in output
        assert "Check connection" in output

    def test_print_info_rich(self, capsys):
        fmt = OutputFormatter(json_mode=False, color=False)
        fmt.print_info("Some info")
        output = capsys.readouterr().out
        assert "Some info" in output

    def test_print_clipboard_copy_rich(self, capsys):
        fmt = OutputFormatter(json_mode=False, color=False)
        fmt.print_clipboard_copy("123456")
        output = capsys.readouterr().out
        assert "123456" in output
