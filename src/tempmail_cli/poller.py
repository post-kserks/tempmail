"""Poller — blocking loop that waits for new messages."""

from __future__ import annotations

import logging
import signal
import time

from tempmail_cli.exceptions import TimeoutWaitingForMailError
from tempmail_cli.models import Account, Message
from tempmail_cli.providers.base import MailProvider

logger = logging.getLogger(__name__)


class Poller:
    """Polls a mail provider for new messages."""

    def __init__(
        self,
        provider: MailProvider,
        account: Account,
        interval: float = 3.0,
        timeout: float = 120.0,
    ) -> None:
        self._provider = provider
        self._account = account
        self._interval = interval
        self._timeout = timeout
        self._interrupted = False

        signal.signal(signal.SIGINT, self._handle_interrupt)
        signal.signal(signal.SIGTERM, self._handle_interrupt)

    def _handle_interrupt(self, signum: int, frame: object) -> None:
        self._interrupted = True
        logger.info("Received interrupt signal")

    def wait_for_message(
        self,
        from_contains: str | None = None,
        subject_contains: str | None = None,
    ) -> Message:
        """Block until a matching message arrives or timeout expires."""
        start = time.monotonic()
        last_id: str | None = None

        while True:
            if self._interrupted:
                raise KeyboardInterrupt("Ожидание прервано пользователем")

            elapsed = time.monotonic() - start
            if elapsed >= self._timeout:
                raise TimeoutWaitingForMailError(
                    f"No mail received within {self._timeout}s timeout.",
                    hint="Try increasing --timeout or check if the sender address is correct.",
                )

            remaining = self._timeout - elapsed
            sleep_time = min(self._interval, remaining)
            if sleep_time > 0:
                time.sleep(sleep_time)

            messages = self._provider.list_messages(self._account, since_id=last_id)

            for msg in messages:
                if self._match(msg, from_contains, subject_contains):
                    full = self._provider.get_message(self._account, msg.id)
                    return full
                last_id = msg.id

    def _match(
        self,
        message: Message,
        from_contains: str | None,
        subject_contains: str | None,
    ) -> bool:
        if from_contains and from_contains.lower() not in message.from_address.lower():
            return False
        if subject_contains and subject_contains.lower() not in message.subject.lower():
            return False
        return True
