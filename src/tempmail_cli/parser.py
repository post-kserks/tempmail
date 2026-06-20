"""Message parser — extracts verification codes and confirmation links from email content."""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

from tempmail_cli.models import Message, ParsedContent

CODE_PATTERNS = [
    re.compile(
        r"(?:код|code|verification code|otp|pin)[\s:\u2013-]{0,5}([A-Za-z0-9]{4,10})",
        re.IGNORECASE,
    ),
    re.compile(r"\b(\d{6})\b"),
    re.compile(r"\b(\d{4})\b"),
    re.compile(r"\b([A-Z0-9]{6,10})\b"),
]

LINK_KEYWORDS = [
    "confirm", "verify", "activate", "validate", "magic", "auth", "sso",
    "подтверд", "активир",
]

EXCLUDE_LINK_KEYWORDS = ["unsubscribe", "privacy", "terms", "preferences"]


def _extract_links_from_html(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []
    for a_tag in soup.find_all("a", href=True):
        href = str(a_tag["href"])
        if href.startswith(("http://", "https://")):
            links.append(href)
    return links


def _score_link(url: str, anchor_text: str) -> int:
    text = (url + " " + anchor_text).lower()
    return sum(1 for kw in LINK_KEYWORDS if kw in text)


def _is_excluded_link(url: str, anchor_text: str) -> bool:
    text = (url + " " + anchor_text).lower()
    return any(kw in text for kw in EXCLUDE_LINK_KEYWORDS)


def _find_codes(text: str) -> list[str]:
    candidates: list[tuple[str, int]] = []
    seen: set[str] = set()

    for pattern in CODE_PATTERNS:
        for match in pattern.finditer(text):
            code = match.group(1) if match.lastindex else match.group(0)
            if code in seen:
                continue
            seen.add(code)
            context = text[max(0, match.start() - 40) : match.end() + 40].lower()
            has_marker = any(
                kw in context
                for kw in ["код", "code", "verification", "otp", "pin", "confirm", "пароль"]
            )
            score = 10 if has_marker else 0
            score += len(code)
            candidates.append((code, score))

    candidates.sort(key=lambda x: x[1], reverse=True)
    return [c[0] for c in candidates]


def _find_best_link(links: list[str]) -> str | None:
    scored: list[tuple[str, int]] = []
    for link in links:
        if _is_excluded_link(link, ""):
            continue
        score = _score_link(link, "")
        scored.append((link, score))
    if not scored:
        return None
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[0][0] if scored[0][1] > 0 else None


def parse_message(message: Message) -> ParsedContent:
    """Parse a message to extract verification codes and confirmation links."""
    text = message.text_body or ""
    html = message.html_body or ""

    all_links: list[str] = []
    if html:
        all_links = _extract_links_from_html(html)

    combined_text = text
    if html:
        soup = BeautifulSoup(html, "html.parser")
        combined_text = text + " " + soup.get_text()

    codes = _find_codes(combined_text)
    best_code = codes[0] if codes else None

    best_link = _find_best_link(all_links)

    return ParsedContent(
        codes=codes,
        links=all_links,
        best_code=best_code,
        best_link=best_link,
    )
