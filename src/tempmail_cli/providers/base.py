"""Abstract base class for mail providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from tempmail_cli.models import Account, Message


class MailProvider(ABC):
    """Contract that all mail provider implementations must fulfill."""

    name: ClassVar[str]
    supports_push: ClassVar[bool] = False

    @abstractmethod
    def list_domains(self) -> list[str]: ...

    @abstractmethod
    def create_account(
        self, domain: str | None = None, username: str | None = None
    ) -> Account: ...

    @abstractmethod
    def list_messages(
        self, account: Account, since_id: str | None = None
    ) -> list[Message]: ...

    @abstractmethod
    def get_message(self, account: Account, message_id: str) -> Message: ...

    @abstractmethod
    def delete_account(self, account: Account) -> None: ...

    def health_check(self) -> bool:
        """Lightweight availability check (default: list_domains)."""
        try:
            self.list_domains()
            return True
        except Exception:
            return False
