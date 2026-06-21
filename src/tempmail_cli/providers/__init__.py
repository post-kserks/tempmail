"""Mail provider implementations."""

from tempmail_cli.providers.base import MailProvider
from tempmail_cli.providers.guerrilla import GuerrillaMailProvider
from tempmail_cli.providers.mailtm import MailTmProvider
from tempmail_cli.providers.tempmail_lol import TempMailLolProvider

__all__ = ["MailProvider", "MailTmProvider", "GuerrillaMailProvider", "TempMailLolProvider"]
