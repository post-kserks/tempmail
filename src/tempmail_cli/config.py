"""Configuration loading with layered priority: defaults → config.yaml → env vars → CLI flags."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from tempmail_cli.exceptions import ConfigError


@dataclass
class ProviderConfig:
    base_url: str
    requests_per_second: float


@dataclass
class DefaultsConfig:
    interval: float = 3.0
    timeout: float = 120.0
    json_output: bool = False
    copy_to_clipboard: bool = False


def _default_providers() -> dict[str, ProviderConfig]:
    return {
        "mailtm": ProviderConfig(
            base_url="https://api.mail.tm",
            requests_per_second=6.0,
        ),
        "guerrilla": ProviderConfig(
            base_url="https://api.guerrillamail.com/ajax.php",
            requests_per_second=0.5,
        ),
    }


@dataclass
class Config:
    default_provider: str = "mailtm"
    providers: dict[str, ProviderConfig] = field(default_factory=_default_providers)
    defaults: DefaultsConfig = field(default_factory=DefaultsConfig)
    color: bool = True
    log_file: str | None = None


def _config_path() -> Path:
    from platformdirs import user_config_dir

    return Path(user_config_dir("tempmail-cli")) / "config.yaml"


def load_config(config_path: Path | None = None) -> Config:
    """Load config with layered priority."""
    path = config_path or _config_path()
    cfg = Config()

    if path.exists():
        try:
            with open(path) as f:
                raw = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ConfigError(f"Invalid config file: {e}") from e

        if "default_provider" in raw:
            cfg.default_provider = raw["default_provider"]
        if "providers" in raw:
            for name, pcfg in raw["providers"].items():
                existing = cfg.providers.get(name)
                cfg.providers[name] = ProviderConfig(
                    base_url=pcfg.get("base_url") or (existing.base_url if existing else ""),
                    requests_per_second=pcfg.get(
                        "requests_per_second", existing.requests_per_second if existing else 1.0
                    ),
                )
        if "defaults" in raw:
            d = raw["defaults"]
            cfg.defaults = DefaultsConfig(
                interval=d.get("interval", cfg.defaults.interval),
                timeout=d.get("timeout", cfg.defaults.timeout),
                json_output=d.get("json_output", cfg.defaults.json_output),
                copy_to_clipboard=d.get("copy_to_clipboard", cfg.defaults.copy_to_clipboard),
            )
        if "output" in raw:
            cfg.color = raw["output"].get("color", cfg.color)

    # Env vars override config file
    if env := os.environ.get("TEMPMAIL_PROVIDER"):
        cfg.default_provider = env
    if env := os.environ.get("TEMPMAIL_TIMEOUT"):
        cfg.defaults.timeout = float(env)
    if env := os.environ.get("TEMPMAIL_INTERVAL"):
        cfg.defaults.interval = float(env)
    env_val = os.environ.get("TEMPMAIL_NO_COLOR")
    if env_val and env_val.lower() not in ("0", "false", "no"):
        cfg.color = False
    if env := os.environ.get("TEMPMAIL_LOG_FILE"):
        cfg.log_file = env

    return cfg
