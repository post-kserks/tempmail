"""Mail.tm provider implementation."""

from __future__ import annotations

import logging
import secrets
from datetime import UTC, datetime
from typing import ClassVar

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from tempmail_cli.exceptions import (
    AuthError,
    MessageNotFoundError,
    ProviderUnavailableError,
    RateLimitedError,
)
from tempmail_cli.models import Account, Message
from tempmail_cli.providers.base import MailProvider
from tempmail_cli.utils.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class MailTmProvider(MailProvider):
    """Mail.tm API implementation."""

    name: ClassVar[str] = "mailtm"

    def __init__(self, base_url: str = "https://api.mail.tm", rps: float = 6.0) -> None:
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
        return session

    def _request(self, method: str, path: str, **kwargs: object) -> requests.Response:
        self._limiter.wait()
        url = f"{self._base_url}{path}"
        try:
            resp = self._session.request(method, url, timeout=10, **kwargs)  # type: ignore[arg-type]
        except requests.ConnectionError as e:
            raise ProviderUnavailableError(
                f"Cannot connect to mail.tm: {e}",
                hint="Check your internet connection or try --provider guerrilla",
            ) from e
        except requests.Timeout as e:
            raise ProviderUnavailableError(
                f"Timeout connecting to mail.tm: {e}",
                hint="Check your internet connection or try --provider guerrilla",
            ) from e

        if resp.status_code == 429:
            raise RateLimitedError("Rate limited by mail.tm")
        if resp.status_code >= 500:
            raise ProviderUnavailableError(
                f"mail.tm server error: {resp.status_code}",
                hint="Try again later or use --provider guerrilla",
            )
        return resp

    def list_domains(self) -> list[str]:
        resp = self._request("GET", "/domains")
        data = resp.json()
        return [d["domain"] for d in data.get("hydra:member", data) if isinstance(d, dict)]

    def create_account(
        self, domain: str | None = None, username: str | None = None
    ) -> Account:
        domains = self.list_domains()
        if not domains:
            raise ProviderUnavailableError("No domains available from mail.tm")
        if domain and domain not in domains:
            options = ", ".join(domains)
            raise ProviderUnavailableError(
                f"Domain {domain} not available. Options: {options}"
            )
        chosen_domain = domain or secrets.choice(domains)
        chosen_username = username or secrets.token_urlsafe(8)
        address = f"{chosen_username}@{chosen_domain}"
        password = secrets.token_urlsafe(16)

        # Create account
        resp = self._request("POST", "/accounts", json={"address": address, "password": password})
        if resp.status_code == 422:
            raise ProviderUnavailableError(f"Failed to create account: {resp.json()}")
        account_data = resp.json()

        # Get token (mail.tm normalizes address to lowercase)
        token_resp = self._request(
            "POST", "/token", json={"address": address.lower(), "password": password}
        )
        if token_resp.status_code == 401:
            raise AuthError("Failed to authenticate with mail.tm")
        token_data = token_resp.json()
        token = token_data.get("token")

        return Account(
            address=address,
            password=password,
            provider="mailtm",
            token=token,
            created_at=datetime.now(UTC),
            raw=account_data,
        )

    def list_messages(
        self, account: Account, since_id: str | None = None
    ) -> list[Message]:
        headers = {"Authorization": f"Bearer {account.token}"}
        resp = self._request("GET", "/messages", headers=headers)
        data = resp.json()

        # Handle error responses
        if isinstance(data, dict) and "code" in data and "message" in data:
            if data["code"] == 401:
                raise AuthError("Session expired or account deleted")
            raise ProviderUnavailableError(f"mail.tm error: {data['message']}")

        messages_raw = data.get("hydra:member", data) if isinstance(data, dict) else data

        messages: list[Message] = []
        for msg in messages_raw:
            if since_id and msg["id"] <= since_id:
                continue
            messages.append(
                Message(
                    id=msg["id"],
                    from_address=msg.get("from", {}).get("address", ""),
                    from_name=msg.get("from", {}).get("name"),
                    subject=msg.get("subject", ""),
                    received_at=datetime.fromisoformat(msg["createdAt"]),
                    text_body=None,  # full body fetched separately
                    html_body=None,
                    seen=msg.get("seen", False),
                )
            )
        return messages

    def get_message(self, account: Account, message_id: str) -> Message:
        headers = {"Authorization": f"Bearer {account.token}"}
        resp = self._request("GET", f"/messages/{message_id}", headers=headers)
        if resp.status_code == 404:
            raise MessageNotFoundError(f"Message {message_id} not found")
        msg = resp.json()

        # Handle html_body - mail.tm may return list or string
        html_body = msg.get("html")
        if isinstance(html_body, list):
            html_body = "\n".join(html_body)

        return Message(
            id=msg["id"],
            from_address=msg.get("from", {}).get("address", ""),
            from_name=msg.get("from", {}).get("name"),
            subject=msg.get("subject", ""),
            received_at=datetime.fromisoformat(msg["createdAt"]),
            text_body=msg.get("text"),
            html_body=html_body,
            seen=msg.get("seen", False),
        )

    def delete_account(self, account: Account) -> None:
        headers = {"Authorization": f"Bearer {account.token}"}
        # Extract account ID from raw data
        account_id = account.raw.get("id")
        if account_id:
            self._request("DELETE", f"/accounts/{account_id}", headers=headers)
