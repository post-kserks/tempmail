"""Guerrilla Mail provider implementation."""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import ClassVar

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

# Guerrilla Mail has limited domain options
GUERRILLA_DOMAINS = [
    "grr.la",
    "guerrillamail.com",
    "guerrillamail.net",
    "guerrillamail.org",
]


class GuerrillaMailProvider(MailProvider):
    """Guerrilla Mail API implementation."""

    name: ClassVar[str] = "guerrilla"

    def __init__(self, base_url: str = "https://api.guerrillamail.com/ajax.php", rps: float = 0.5) -> None:
        self._base_url = base_url
        self._limiter = RateLimiter(rps)
        self._session = self._build_session()

    @staticmethod
    def _build_session() -> requests.Session:
        session = requests.Session()
        retry = Retry(total=3, backoff_factor=0.5, status_forcelist=[502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    def _request(self, **params: str) -> dict:
        self._limiter.wait()
        try:
            resp = self._session.get(self._base_url, params=params, timeout=10)
        except requests.ConnectionError as e:
            raise ProviderUnavailableError(
                f"Cannot connect to Guerrilla Mail: {e}",
                hint="Check your internet connection or try --provider mailtm",
            ) from e
        except requests.Timeout as e:
            raise ProviderUnavailableError(
                f"Timeout connecting to Guerrilla Mail: {e}",
                hint="Check your internet connection or try --provider mailtm",
            ) from e

        if resp.status_code == 429:
            raise RateLimitedError("Rate limited by Guerrilla Mail")
        if resp.status_code >= 500:
            raise ProviderUnavailableError(
                f"Guerrilla Mail server error: {resp.status_code}",
                hint="Try again later or use --provider mailtm",
            )
        return resp.json()

    def list_domains(self) -> list[str]:
        return list(GUERRILLA_DOMAINS)

    def create_account(
        self, domain: str | None = None, username: str | None = None
    ) -> Account:
        chosen_domain = domain or secrets.choice(GUERRILLA_DOMAINS)
        chosen_username = username or secrets.token_urlsafe(8)
        full_address = f"{chosen_username}@{chosen_domain}"

        data = self._request(f="set_email_user", email_user=chosen_username)
        sid_token = data.get("sid_token", "")
        email_addr = data.get("email_addr", full_address)

        return Account(
            address=email_addr,
            password="",  # Guerrilla Mail doesn't use passwords
            provider="guerrilla",
            token=sid_token,
            created_at=datetime.now(timezone.utc),
            raw=data,
        )

    def list_messages(
        self, account: Account, since_id: str | None = None
    ) -> list[Message]:
        data = self._request(f="check_email", seq=since_id or "0", sid_token=account.token or "")
        messages_raw = data.get("list", [])

        messages: list[Message] = []
        for msg in messages_raw:
            if since_id and str(msg.get("mail_id", "")) <= since_id:
                continue
            messages.append(
                Message(
                    id=str(msg.get("mail_id", "")),
                    from_address=msg.get("mail_from", ""),
                    from_name=None,
                    subject=msg.get("mail_subject", ""),
                    received_at=datetime.fromtimestamp(msg.get("mail_date", 0), tz=timezone.utc),
                    text_body=None,
                    html_body=None,
                    seen=msg.get("mail_read", "0") == "1",
                )
            )
        return messages

    def get_message(self, account: Account, message_id: str) -> Message:
        data = self._request(
            f="fetch_email",
            email_id=message_id,
            sid_token=account.token or "",
        )
        msg = data.get("mail_body", "")
        subject = data.get("mail_subject", "")
        sender = data.get("mail_from", "")
        text = data.get("mail_text", "")

        # Extract message ID from the response
        mid = data.get("mail_id", message_id)

        return Message(
            id=str(mid),
            from_address=sender,
            from_name=None,
            subject=subject,
            received_at=datetime.now(timezone.utc),
            text_body=text or None,
            html_body=msg or None,
            seen=False,
        )

    def delete_account(self, account: Account) -> None:
        # Guerrilla Mail doesn't actually delete - just forgets the session
        self._request(f="forget_me", sid_token=account.token or "")
