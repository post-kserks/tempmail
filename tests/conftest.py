"""Shared test fixtures."""

import pytest
from datetime import datetime, timezone

from tempmail_cli.models import Account


@pytest.fixture
def sample_account() -> Account:
    return Account(
        address="test@example.com",
        password="secret123",
        provider="mailtm",
        token="fake-jwt-token",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        raw={"id": "acc-123"},
    )
