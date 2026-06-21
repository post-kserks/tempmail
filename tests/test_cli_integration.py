"""Integration tests for CLI commands."""

import re
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from tempmail_cli.cli import app

runner = CliRunner()


def strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from text."""
    ansi_escape = re.compile(r"\x1b\[[0-9;]*m")
    return ansi_escape.sub("", text)


class TestCLIIntegration:
    def test_version(self):
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "tempmail" in strip_ansi(result.output)

    def test_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        output = strip_ansi(result.output)
        assert "new" in output
        assert "watch" in output
        assert "inbox" in output
        assert "read" in output
        assert "providers" in output
        assert "close" in output

    def test_new_help(self):
        result = runner.invoke(app, ["new", "--help"])
        assert result.exit_code == 0
        output = strip_ansi(result.output)
        assert "--provider" in output
        assert "--domain" in output

    def test_watch_help(self):
        result = runner.invoke(app, ["watch", "--help"])
        assert result.exit_code == 0
        output = strip_ansi(result.output)
        assert "--interval" in output
        assert "--timeout" in output
        assert "--from" in output
        assert "--copy" in output

    def test_inbox_help(self):
        result = runner.invoke(app, ["inbox", "--help"])
        assert result.exit_code == 0
        output = strip_ansi(result.output)
        assert "--limit" in output

    @patch("tempmail_cli.cli.list_providers")
    @patch("tempmail_cli.cli.load_config")
    def test_providers_command(self, mock_load_config, mock_list_providers):
        mock_cfg = MagicMock()
        mock_cfg.default_provider = "mailtm"
        mock_load_config.return_value = mock_cfg

        mock_cls = MagicMock()
        mock_cls.supports_push = True
        mock_cls.return_value.health_check.return_value = True
        mock_list_providers.return_value = {"mailtm": mock_cls}

        result = runner.invoke(app, ["providers"])
        assert result.exit_code == 0
        assert "mailtm" in strip_ansi(result.output)

    @patch("tempmail_cli.cli.list_providers")
    @patch("tempmail_cli.cli.load_config")
    def test_providers_command_offline(self, mock_load_config, mock_list_providers):
        mock_cfg = MagicMock()
        mock_cfg.default_provider = "mailtm"
        mock_load_config.return_value = mock_cfg

        mock_cls = MagicMock()
        mock_cls.supports_push = False
        mock_cls.return_value.health_check.return_value = False
        mock_list_providers.return_value = {"mailtm": mock_cls}

        result = runner.invoke(app, ["providers"])
        assert result.exit_code == 0
        assert "mailtm" in strip_ansi(result.output)

    @patch("tempmail_cli.cli.list_providers")
    @patch("tempmail_cli.cli.load_config")
    def test_providers_json(self, mock_load_config, mock_list_providers):
        mock_cfg = MagicMock()
        mock_cfg.default_provider = "mailtm"
        mock_load_config.return_value = mock_cfg

        mock_cls = MagicMock()
        mock_cls.supports_push = True
        mock_cls.return_value.health_check.return_value = True
        mock_list_providers.return_value = {"mailtm": mock_cls}

        result = runner.invoke(app, ["providers", "--json"])
        assert result.exit_code == 0
        assert "mailtm" in strip_ansi(result.output)
