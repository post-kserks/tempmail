"""Tests for configuration loading."""

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from tempmail_cli.config import Config, DefaultsConfig, ProviderConfig, load_config
from tempmail_cli.exceptions import ConfigError


@pytest.fixture
def default_config():
    return load_config(config_path=Path("/nonexistent/config.yaml"))


@pytest.fixture
def config_with_providers(tmp_path):
    config_data = {
        "default_provider": "guerrilla",
        "providers": {
            "custom": {
                "base_url": "https://custom.api",
                "requests_per_second": 2.0,
            }
        },
        "defaults": {
            "interval": 5.0,
            "timeout": 60.0,
            "json_output": True,
            "copy_to_clipboard": True,
        },
        "output": {
            "color": False,
        },
    }
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump(config_data))
    return config_path


class TestLoadConfig:
    def test_default_config(self, default_config):
        assert default_config.default_provider == "mailtm"
        assert "mailtm" in default_config.providers
        assert "guerrilla" in default_config.providers
        assert default_config.defaults.interval == 3.0
        assert default_config.defaults.timeout == 120.0
        assert default_config.defaults.json_output is False
        assert default_config.defaults.copy_to_clipboard is False
        assert default_config.color is True
        assert default_config.log_file is None

    def test_config_with_providers(self, config_with_providers):
        cfg = load_config(config_path=config_with_providers)
        assert cfg.default_provider == "guerrilla"
        assert "custom" in cfg.providers
        assert cfg.providers["custom"].base_url == "https://custom.api"
        assert cfg.providers["custom"].requests_per_second == 2.0
        assert cfg.defaults.interval == 5.0
        assert cfg.defaults.timeout == 60.0
        assert cfg.defaults.json_output is True
        assert cfg.defaults.copy_to_clipboard is True
        assert cfg.color is False

    def test_env_var_override_provider(self, monkeypatch, config_with_providers):
        monkeypatch.setenv("TEMPMAIL_PROVIDER", "env_provider")
        cfg = load_config(config_path=config_with_providers)
        assert cfg.default_provider == "env_provider"

    def test_env_var_override_timeout(self, monkeypatch, config_with_providers):
        monkeypatch.setenv("TEMPMAIL_TIMEOUT", "30.0")
        cfg = load_config(config_path=config_with_providers)
        assert cfg.defaults.timeout == 30.0

    def test_env_var_override_interval(self, monkeypatch, config_with_providers):
        monkeypatch.setenv("TEMPMAIL_INTERVAL", "10.0")
        cfg = load_config(config_path=config_with_providers)
        assert cfg.defaults.interval == 10.0

    def test_env_var_override_no_color(self, monkeypatch, default_config):
        monkeypatch.setenv("TEMPMAIL_NO_COLOR", "1")
        cfg = load_config(config_path=Path("/nonexistent/config.yaml"))
        assert cfg.color is False

    def test_env_var_override_log_file(self, monkeypatch, default_config):
        monkeypatch.setenv("TEMPMAIL_LOG_FILE", "/tmp/tempmail.log")
        cfg = load_config(config_path=Path("/nonexistent/config.yaml"))
        assert cfg.log_file == "/tmp/tempmail.log"

    def test_invalid_yaml_raises_config_error(self, tmp_path):
        config_path = tmp_path / "bad.yaml"
        config_path.write_text("{{invalid yaml: [")
        with pytest.raises(ConfigError, match="Invalid config file"):
            load_config(config_path=config_path)

    def test_partial_config_file(self, tmp_path):
        config_data = {"default_provider": "custom"}
        config_path = tmp_path / "config.yaml"
        config_path.write_text(yaml.dump(config_data))
        cfg = load_config(config_path=config_path)
        assert cfg.default_provider == "custom"
        assert "mailtm" in cfg.providers
        assert cfg.defaults.interval == 3.0

    def test_empty_config_file(self, tmp_path):
        config_path = tmp_path / "config.yaml"
        config_path.write_text("")
        cfg = load_config(config_path=config_path)
        assert cfg.default_provider == "mailtm"

    def test_provider_defaults_not_overridden(self, tmp_path):
        config_data = {"providers": {"mailtm": {"base_url": "https://custom.mail.tm"}}}
        config_path = tmp_path / "config.yaml"
        config_path.write_text(yaml.dump(config_data))
        cfg = load_config(config_path=config_path)
        assert cfg.providers["mailtm"].base_url == "https://custom.mail.tm"
        assert cfg.providers["mailtm"].requests_per_second == 6.0
        assert cfg.providers["guerrilla"].base_url == "https://api.guerrillamail.com/ajax.php"

    def test_output_color_default(self, default_config):
        assert default_config.color is True
