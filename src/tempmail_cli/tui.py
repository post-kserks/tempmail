"""TUI interface for TempMail CLI using urwid."""

from __future__ import annotations

import urwid

from tempmail_cli.clipboard import copy_to_clipboard
from tempmail_cli.exceptions import TempMailError
from tempmail_cli.models import Account, Message, ParsedContent
from tempmail_cli.parser import parse_message
from tempmail_cli.poller import Poller
from tempmail_cli.provider_manager import list_providers, resolve
from tempmail_cli.session_store import (
    delete_session,
    load_session,
    save_session,
)


class TempMailUrwid:
    """TempMail TUI Application using urwid."""

    def __init__(self) -> None:
        self.account: Account | None = None
        self.messages: list[Message] = []
        self.current_message: Message | None = None
        self.parsed: ParsedContent | None = None

        # Widgets
        self.inbox_list: urwid.ListBox | None = None
        self.message_text: urwid.Text | None = None
        self.status_text: urwid.Text | None = None

        # Build UI
        self._build_ui()

    def _build_ui(self) -> None:
        """Build the TUI layout."""
        # Header
        header = urwid.Text(" TempMail CLI ", align="center")
        header = urwid.AttrMap(header, "header")

        # Sidebar - Inbox
        self.inbox_list = urwid.ListBox(urwid.SimpleFocusListWalker([]))
        inbox_box = urwid.LineBox(self.inbox_list, title="Inbox")

        # Main - Message view
        self.message_text = urwid.Text("Select a message to read")
        self.message_text = urwid.AttrMap(self.message_text, "body")
        message_box = urwid.LineBox(self.message_text, title="Message")

        # Status bar
        self.status_text = urwid.Text(" Press 'n' new | 'w' watch | 'r' refresh | 'q' quit ")
        self.status_text = urwid.AttrMap(self.status_text, "status")

        # Layout
        left_column = urwid.Columns([
            ("weight", 3, inbox_box),
        ])
        right_column = urwid.Columns([
            ("weight", 5, message_box),
        ])

        main_columns = urwid.Columns([
            ("weight", 3, left_column),
            ("weight", 5, right_column),
        ])

        # Main frame
        self.main_widget = urwid.Frame(
            body=main_columns,
            header=header,
            footer=self.status_text,
        )

        # Load session
        self._load_session()

    def _load_session(self) -> None:
        """Try to load existing session."""
        try:
            self.account = load_session()
            self._update_status(f"Session loaded: {self.account.address}")
            self._refresh_inbox()
        except TempMailError:
            self._update_status("No active session. Press 'n' to create one.")

    def _update_status(self, message: str) -> None:
        """Update status bar."""
        if self.account:
            text = f" {self.account.address} | {message}"
        else:
            text = f" {message}"
        if self.status_text and hasattr(self.status_text, 'original_widget'):
            self.status_text.original_widget.set_text(text)

    def _refresh_inbox(self) -> None:
        """Refresh inbox messages."""
        if not self.account:
            return
        try:
            prov = resolve(self.account.provider)
            self.messages = prov.list_messages(self.account)
            self._render_inbox()
        except TempMailError as e:
            self._update_status(f"Error: {e}")

    def _render_inbox(self) -> None:
        """Render inbox list."""
        if not self.inbox_list:
            return

        walker = urwid.SimpleFocusListWalker([])
        for msg in self.messages:
            date_str = msg.received_at.strftime("%H:%M")
            text = f"{msg.from_address.split('@')[0]:12} {msg.subject[:25]:25} {date_str}"
            item = urwid.SelectableIcon(text)
            walker.append(urwid.AttrMap(item, "inbox_item"))
        self.inbox_list.body = walker
        self._update_status(f"Inbox: {len(self.messages)} messages")

    def _render_message(self, message: Message, parsed: ParsedContent) -> None:
        """Render message content."""
        self.current_message = message
        self.parsed = parsed

        lines = [
            f"From: {message.from_address}",
            f"Subject: {message.subject}",
            f"Date: {message.received_at.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "─" * 40,
        ]
        if parsed.best_code:
            lines.append(f"🔑 Code: {parsed.best_code}")
            lines.append("")
        if parsed.best_link:
            lines.append(f"🔗 Link: {parsed.best_link}")
            lines.append("")
        if len(parsed.codes) > 1:
            other = [c for c in parsed.codes if c != parsed.best_code]
            lines.append(f"Other codes: {', '.join(other)}")
            lines.append("")
        lines.append("─" * 40)
        lines.append("")
        body = message.text_body or message.html_body or "(no content)"
        lines.append(body[:2000])

        if self.message_text and hasattr(self.message_text, 'original_widget'):
            self.message_text.original_widget.set_text("\n".join(lines))

    def keypress(self, size: tuple[int, int], key: str) -> str | None:
        """Handle key presses."""
        if key == "q":
            raise urwid.ExitMainLoop()
        elif key == "n":
            self._create_mailbox()
        elif key == "w":
            self._watch()
        elif key == "r":
            self._refresh_inbox()
        elif key == "y":
            self._copy_email()
        elif key == "o":
            self._copy_code()
        elif key == "m":
            self._copy_message()
        elif key == "enter":
            self._open_selected_message()
        elif key == "up":
            if self.inbox_list:
                self.inbox_list.focus_position = max(0, self.inbox_list.focus_position - 1)
        elif key == "down":
            if self.inbox_list:
                self.inbox_list.focus_position = min(
                    len(self.inbox_list.body) - 1,
                    self.inbox_list.focus_position + 1
                )
        return key

    def _create_mailbox(self) -> None:
        """Create new mailbox."""
        self._update_status("Creating new mailbox...")
        try:
            prov = resolve()
            self.account = prov.create_account()
            save_session(self.account)
            self._update_status(f"Created: {self.account.address}")
            self._refresh_inbox()
        except TempMailError as e:
            self._update_status(f"Error: {e}")

    def _watch(self) -> None:
        """Watch for new emails."""
        if not self.account:
            self._update_status("No session. Press 'n' to create mailbox.")
            return

        self._update_status("Watching for new emails... (60s timeout)")

        try:
            prov = resolve(self.account.provider)
            poller = Poller(prov, self.account, interval=3.0, timeout=60.0)
            message = poller.wait_for_message()
            parsed = parse_message(message)
            self._render_message(message, parsed)
            self._update_status(f"New message from: {message.from_address}")
            self._refresh_inbox()
        except TempMailError as e:
            self._update_status(f"Watch stopped: {e}")
        except KeyboardInterrupt:
            self._update_status("Watch stopped by user")

    def _open_selected_message(self) -> None:
        """Open selected message from inbox."""
        if not self.inbox_list or not self.messages:
            return

        idx = self.inbox_list.focus_position
        if idx < len(self.messages):
            msg = self.messages[idx]
            try:
                prov = resolve(self.account.provider)
                full_msg = prov.get_message(self.account, msg.id)
                parsed = parse_message(full_msg)
                self._render_message(full_msg, parsed)
            except TempMailError as e:
                self._update_status(f"Error: {e}")

    def _copy_email(self) -> None:
        """Copy email address to clipboard."""
        if self.account:
            copy_to_clipboard(self.account.address)
            self._update_status("📋 Email copied!")

    def _copy_code(self) -> None:
        """Copy verification code to clipboard."""
        if self.parsed and self.parsed.best_code:
            copy_to_clipboard(self.parsed.best_code)
            self._update_status(f"📋 Code {self.parsed.best_code} copied!")
        elif self.account:
            copy_to_clipboard(self.account.address)
            self._update_status("📋 Email copied (no code)!")

    def _copy_message(self) -> None:
        """Copy entire message to clipboard."""
        if self.current_message:
            msg = self.current_message
            lines = [
                f"From: {msg.from_address}",
                f"Subject: {msg.subject}",
                f"Date: {msg.received_at.strftime('%Y-%m-%d %H:%M:%S')}",
                "",
                msg.text_body or "",
            ]
            copy_to_clipboard("\n".join(lines))
            self._update_status("📋 Message copied!")

    def run(self) -> None:
        """Run the TUI application."""
        # Define palette
        palette = [
            ("header", "white", "dark blue"),
            ("status", "white", "dark green"),
            ("inbox_item", "light gray", "black"),
            ("inbox_item_focus", "white", "dark blue"),
            ("body", "light gray", "black"),
        ]

        # Create main loop
        self.loop = urwid.MainLoop(
            self.main_widget,
            palette=palette,
            unhandled_input=self.keypress,
        )

        # Enable mouse support
        self.loop.screen.set_mouse_tracking()

        self.loop.run()


def main() -> None:
    """Run the TUI application."""
    app = TempMailUrwid()
    app.run()


if __name__ == "__main__":
    main()
