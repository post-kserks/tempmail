"""Tests for Mail.tm provider with mocked HTTP."""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
import responses

from tempmail_cli.exceptions import RateLimitedError
from tempmail_cli.models import Account
from tempmail_cli.providers.mailtm import MailTmProvider

FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def provider():
    return MailTmProvider(base_url="https://api.mail.tm", rps=100.0)


@pytest.fixture
def mailtm_responses():
    return json.loads((FIXTURES / "mailtm_responses.json").read_text())


@pytest.fixture
def sample_account():
    return Account(
        address="test@example.com",
        password="pass",
        provider="mailtm",
        token="fake-token",
        created_at=datetime.now(UTC),
    )


class TestMailTmProvider:
    @responses.activate
    def test_list_domains(self, provider, mailtm_responses):
        responses.add(
            responses.GET,
            "https://api.mail.tm/domains",
            json=mailtm_responses["domains"],
            status=200,
        )
        domains = provider.list_domains()
        assert "example.com" in domains

    @responses.activate
    def test_create_account(self, provider, mailtm_responses):
        responses.add(
            responses.GET,
            "https://api.mail.tm/domains",
            json=mailtm_responses["domains"],
            status=200,
        )
        responses.add(
            responses.POST,
            "https://api.mail.tm/accounts",
            json=mailtm_responses["account"],
            status=201,
        )
        responses.add(
            responses.POST,
            "https://api.mail.tm/token",
            json=mailtm_responses["token"],
            status=200,
        )
        account = provider.create_account(domain="example.com", username="testuser")
        assert account.address == "testuser@example.com"
        assert account.token is not None
        assert account.provider == "mailtm"

    @responses.activate
    def test_list_messages(self, provider, mailtm_responses, sample_account):
        responses.add(
            responses.GET,
            "https://api.mail.tm/messages",
            json=mailtm_responses["messages"],
            status=200,
        )
        messages = provider.list_messages(sample_account)
        assert len(messages) == 1
        assert messages[0].subject == "Confirm your email"

    @responses.activate
    def test_get_message(self, provider, mailtm_responses, sample_account):
        responses.add(
            responses.GET,
            "https://api.mail.tm/messages/msg-1",
            json=mailtm_responses["message_detail"],
            status=200,
        )
        msg = provider.get_message(sample_account, "msg-1")
        assert msg.text_body == "Your code is 123456"

    @responses.activate
    def test_health_check(self, provider, mailtm_responses):
        responses.add(
            responses.GET,
            "https://api.mail.tm/domains",
            json=mailtm_responses["domains"],
            status=200,
        )
        assert provider.health_check() is True

    @responses.activate
    def test_health_check_failure(self, provider):
        responses.add(
            responses.GET,
            "https://api.mail.tm/domains",
            json={"error": "unavailable"},
            status=503,
        )
        assert provider.health_check() is False

    @responses.activate
    def test_rate_limit_error(self, provider):
        responses.add(
            responses.GET,
            "https://api.mail.tm/domains",
            json={"error": "rate limited"},
            status=429,
        )
        with pytest.raises(RateLimitedError):
            provider.list_domains()
