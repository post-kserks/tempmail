"""Tests for provider manager."""

from unittest.mock import MagicMock, patch

import pytest

from tempmail_cli.exceptions import ProviderUnavailableError
from tempmail_cli.provider_manager import create_provider, list_providers, resolve


class TestProviderManager:
    def test_list_providers(self):
        providers = list_providers()
        assert "mailtm" in providers
        assert "guerrilla" in providers

    @patch("tempmail_cli.provider_manager.load_config")
    def test_resolve_default(self, mock_config):
        mock_config.return_value = MagicMock(default_provider="mailtm", providers={})
        with patch("tempmail_cli.provider_manager.create_provider") as mock_create:
            mock_provider = MagicMock()
            mock_provider.health_check.return_value = True
            mock_create.return_value = mock_provider
            result = resolve()
            assert result == mock_provider

    @patch("tempmail_cli.provider_manager.load_config")
    def test_resolve_unavailable(self, mock_config):
        mock_config.return_value = MagicMock(default_provider="mailtm", providers={})
        with patch("tempmail_cli.provider_manager.create_provider") as mock_create:
            mock_provider = MagicMock()
            mock_provider.health_check.return_value = False
            mock_create.return_value = mock_provider
            with pytest.raises(ProviderUnavailableError):
                resolve()

    def test_create_unknown_provider(self):
        with pytest.raises(ProviderUnavailableError):
            create_provider("unknown_provider")
