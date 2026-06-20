"""Tests for Guerrilla Mail provider with mocked HTTP."""

import pytest
import responses

from tempmail_cli.providers.guerrilla import GuerrillaMailProvider, GUERRILLA_DOMAINS
from tempmail_cli.models import Account
from datetime import datetime, timezone


@pytest.fixture
def provider():
    return GuerrillaMailProvider(rps=100.0)


class TestGuerrillaMailProvider:
    @responses.activate
    def test_list_domains(self, provider):
        domains = provider.list_domains()
        assert len(domains) > 0
        assert "guerrillamail.com" in domains

    @responses.activate
    def test_create_account(self, provider):
        responses.add(
            responses.GET,
            "https://api.guerrillamail.com/ajax.php",
            json={
                "sid_token": "fake-sid",
                "email_addr": "test@grr.la",
            },
            status=200,
            match_querystring=False,
        )
        account = provider.create_account(domain="grr.la", username="test")
        assert account.address == "test@grr.la"
        assert account.token == "fake-sid"

    @responses.activate
    def test_list_messages(self, provider):
        responses.add(
            responses.GET,
            "https://api.guerrillamail.com/ajax.php",
            json={
                "list": [
                    {
                        "mail_id": "1",
                        "mail_from": "sender@test.com",
                        "mail_subject": "Test",
                        "mail_date": 1718889600,
                        "mail_read": "0",
                    }
                ]
            },
            status=200,
            match_querystring=False,
        )
        account = Account(
            address="test@grr.la",
            password="",
            provider="guerrilla",
            token="fake-sid",
            created_at=datetime.now(timezone.utc),
        )
        messages = provider.list_messages(account)
        assert len(messages) == 1

    @responses.activate
    def test_health_check(self, provider):
        assert provider.health_check() is True
