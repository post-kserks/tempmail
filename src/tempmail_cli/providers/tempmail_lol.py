"""TempMail.lol provider implementation."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, ClassVar

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from tempmail_cli.exceptions import (
    ProviderUnavailableError,
    RateLimitedError,
)
from tempmail_cli.models import Account, Message
from tempmail_cli.providers.base import MailProvider
from tempmail_cli.utils.rate_limiter import RateLimiter


class TempMailLolProvider(MailProvider):
    """TempMail.lol API implementation."""

    name: ClassVar[str] = "tempmail-lol"
    supports_push: ClassVar[bool] = False

    def __init__(
        self, base_url: str = "https://api.tempmail.lol/v2", rps: float = 1.0
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._limiter = RateLimiter(rps)
        self._session = self._build_session()

    @staticmethod
    def _build_session() -> requests.Session:
        session = requests.Session()
        retry = Retry(total=3, backoff_factor=0.5, status_forcelist=[502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        session.headers.update({
            "User-Agent": "TempMailCLI/0.1.0",
            "Accept": "application/json",
        })
        return session

    def _request(
        self, method: str, path: str, **kwargs: Any
    ) -> requests.Response:
        self._limiter.wait()
        url = f"{self._base_url}{path}"
        try:
            resp = self._session.request(method, url, timeout=10, **kwargs)
        except requests.ConnectionError as e:
            raise ProviderUnavailableError(
                f"Cannot connect to TempMail.lol: {e}",
                hint="Check your internet connection or try --provider mailtm",
            ) from e
        except requests.Timeout as e:
            raise ProviderUnavailableError(
                f"Timeout connecting to TempMail.lol: {e}",
                hint="Check your internet connection or try --provider mailtm",
            ) from e

        if resp.status_code == 429:
            raise RateLimitedError("Rate limited by TempMail.lol")
        if resp.status_code >= 500:
            raise ProviderUnavailableError(
                f"TempMail.lol server error: {resp.status_code}",
                hint="Try again later or use --provider mailtm",
            )
        return resp

    def list_domains(self) -> list[str]:
        # TempMail.lol doesn't expose a domains endpoint
        # Domains are dynamic and change frequently
        return []

    def create_account(
        self, domain: str | None = None, username: str | None = None
    ) -> Account:
        payload: dict[str, Any] = {}
        if domain:
            payload["domain"] = domain
        if username:
            payload["prefix"] = username

        resp = self._request("POST", "/inbox/create", json=payload)
        if resp.status_code == 403:
            error_data = resp.json()
            raise ProviderUnavailableError(
                f"TempMail.lol access denied: {error_data.get('error', 'Unknown')}",
                hint="Your region may be blocked. Try --provider mailtm or --provider guerrilla",
            )
        data = resp.json()

        address = data.get("address", "")
        token = data.get("token", "")

        return Account(
            address=address,
            password="",  # TempMail.lol doesn't use passwords
            provider="tempmail-lol",
            token=token,
            created_at=datetime.now(UTC),
            raw=data,
        )

    def list_messages(
        self, account: Account, since_id: str | None = None
    ) -> list[Message]:
        resp = self._request("GET", f"/inbox?token={account.token}")
        data = resp.json()

        if data.get("expired"):
            raise ProviderUnavailableError(
                "Session expired. Run `tempmail new` to create a new mailbox.",
                hint="TempMail.lol tokens expire after some time.",
            )

        emails_raw = data.get("emails") or []
        messages: list[Message] = []

        for i, email in enumerate(emails_raw):
            msg_id = str(i)
            if since_id and msg_id <= since_id:
                continue

            messages.append(
                Message(
                    id=msg_id,
                    from_address=email.get("from", ""),
                    from_name=None,
                    subject=email.get("subject", ""),
                    received_at=datetime.now(UTC),
                    text_body=email.get("body"),
                    html_body=email.get("html"),
                    seen=False,
                )
            )
        return messages

    def get_message(self, account: Account, message_id: str) -> Message:
        # TempMail.lol returns all emails in the inbox, we need to find the specific one
        resp = self._request("GET", f"/inbox?token={account.token}")
        data = resp.json()

        emails_raw = data.get("emails") or []
        idx = int(message_id) if message_id.isdigit() else -1

        if idx < 0 or idx >= len(emails_raw):
            from tempmail_cli.exceptions import MessageNotFoundError
            raise MessageNotFoundError(f"Message {message_id} not found")

        email = emails_raw[idx]

        return Message(
            id=message_id,
            from_address=email.get("from", ""),
            from_name=None,
            subject=email.get("subject", ""),
            received_at=datetime.now(UTC),
            text_body=email.get("body"),
            html_body=email.get("html"),
            seen=False,
        )

    def delete_account(self, account: Account) -> None:
        # TempMail.lol doesn't have a delete endpoint
        # Tokens expire automatically
        pass
