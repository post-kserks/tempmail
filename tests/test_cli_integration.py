"""Integration tests for CLI commands."""

import pytest
from typer.testing import CliRunner

from tempmail_cli.cli import app

runner = CliRunner()


class TestCLIIntegration:
    def test_version(self):
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "tempmail" in result.output

    def test_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "new" in result.output
        assert "watch" in result.output
        assert "inbox" in result.output
        assert "read" in result.output
        assert "providers" in result.output
        assert "close" in result.output

    def test_new_help(self):
        result = runner.invoke(app, ["new", "--help"])
        assert result.exit_code == 0
        assert "--provider" in result.output
        assert "--domain" in result.output

    def test_watch_help(self):
        result = runner.invoke(app, ["watch", "--help"])
        assert result.exit_code == 0
        assert "--interval" in result.output
        assert "--timeout" in result.output
        assert "--from" in result.output
        assert "--copy" in result.output

    def test_inbox_help(self):
        result = runner.invoke(app, ["inbox", "--help"])
        assert result.exit_code == 0
        assert "--limit" in result.output
