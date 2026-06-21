"""Clipboard wrapper with graceful fallback."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def copy_to_clipboard(text: str) -> bool:
    """Copy text to system clipboard. Returns True on success."""
    try:
        import pyperclip

        pyperclip.copy(text)
        return True
    except Exception:
        logger.warning("Could not copy to clipboard: no clipboard mechanism available")
        return False
