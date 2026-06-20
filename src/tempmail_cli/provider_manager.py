"""Provider selection, health check, and fallback logic."""

from __future__ import annotations

import logging

from tempmail_cli.config import load_config
from tempmail_cli.exceptions import ProviderUnavailableError
from tempmail_cli.providers.base import MailProvider
from tempmail_cli.providers.guerrilla import GuerrillaMailProvider
from tempmail_cli.providers.mailtm import MailTmProvider

logger = logging.getLogger(__name__)

_REGISTRY: dict[str, type[MailProvider]] = {
    "mailtm": MailTmProvider,
    "guerrilla": GuerrillaMailProvider,
}


def list_providers() -> dict[str, type[MailProvider]]:
    """Return all registered provider classes."""
    return dict(_REGISTRY)


def create_provider(name: str) -> MailProvider:
    """Instantiate a provider by name with config-based settings."""
    cfg = load_config()
    provider_class = _REGISTRY.get(name)
    if not provider_class:
        raise ProviderUnavailableError(
            f"Unknown provider: {name}",
            hint=f"Available providers: {', '.join(_REGISTRY.keys())}",
        )
    pcfg = cfg.providers.get(name)
    if name == "mailtm":
        return MailTmProvider(
            base_url=pcfg.base_url if pcfg else "https://api.mail.tm",
            rps=pcfg.requests_per_second if pcfg else 6.0,
        )
    if name == "guerrilla":
        return GuerrillaMailProvider(
            base_url=pcfg.base_url if pcfg else "https://api.guerrillamail.com/ajax.php",
            rps=pcfg.requests_per_second if pcfg else 0.5,
        )
    return provider_class()


def resolve(name: str | None = None) -> MailProvider:
    """Resolve provider with health check and fallback suggestion."""
    cfg = load_config()
    chosen = name or cfg.default_provider
    provider = create_provider(chosen)

    if not provider.health_check():
        alternatives = [n for n in _REGISTRY if n != chosen]
        hint = None
        if alternatives:
            alt = alternatives[0]
            hint = f"Try --provider {alt}"
        raise ProviderUnavailableError(
            f"Provider '{chosen}' is unavailable",
            hint=hint,
        )

    return provider
