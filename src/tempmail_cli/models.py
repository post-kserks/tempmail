"""Data models for TempMail CLI."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class Account:
    address: str
    password: str
    provider: str
    token: str | None
    created_at: datetime
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Message:
    id: str
    from_address: str
    from_name: str | None
    subject: str
    received_at: datetime
    text_body: str | None
    html_body: str | None
    seen: bool


@dataclass(frozen=True)
class ParsedContent:
    codes: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    best_code: str | None = None
    best_link: str | None = None
