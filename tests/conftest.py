"""Shared test fixtures."""

from datetime import UTC, datetime

import pytest

from tempmail_cli.models import Account


@pytest.fixture
def sample_account() -> Account:
    return Account(
        address="test@example.com",
        password="secret123",
        provider="mailtm",
        token="fake-jwt-token",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        raw={"id": "acc-123"},
    )
