"""Mail provider implementations."""

from tempmail_cli.providers.base import MailProvider
from tempmail_cli.providers.mailtm import MailTmProvider

__all__ = ["MailProvider", "MailTmProvider"]
