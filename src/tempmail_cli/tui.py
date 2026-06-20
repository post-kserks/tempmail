"""TUI interface for TempMail CLI using Textual."""

from __future__ import annotations

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import (
    DataTable,
    Footer,
    Header,
    Label,
    LoadingIndicator,
    RichLog,
    Static,
)

from tempmail_cli.exceptions import TempMailError
from tempmail_cli.models import Account, Message, ParsedContent
from tempmail_cli.output import OutputFormatter
from tempmail_cli.parser import parse_message
from tempmail_cli.poller import Poller
from tempmail_cli.provider_manager import create_provider, list_providers, resolve
from tempmail_cli.session_store import (
    delete_session,
    load_session,
    save_session,
    session_exists,
)


class TempMailTUI(App):
    """TempMail TUI Application."""

    TITLE = "TempMail CLI"
    SUB_TITLE = "Temporary Email Client"

    CSS = """
    Screen {
        layout: horizontal;
    }

    #sidebar {
        width: 30%;
        border: solid $primary;
        padding: 1;
    }

    #main {
        width: 70%;
        padding: 1;
    }

    #inbox-table {
        height: 1fr;
    }

    #message-view {
        height: 1fr;
        overflow: auto;
    }

    #status-bar {
        height: 3;
        dock: bottom;
        padding: 0 1;
        background: $surface;
        border-top: solid $primary;
    }

    .email-header {
        padding: 1;
        background: $surface;
        margin: 0 0 1 0;
    }

    .email-code {
        padding: 1;
        background: $success;
        color: $text;
        margin: 1 0;
        text-align: center;
    }

    .email-link {
        padding: 1;
        background: $primary;
        color: $text;
        margin: 1 0;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("n", "new_mailbox", "New Mailbox"),
        Binding("w", "watch", "Watch"),
        Binding("r", "refresh", "Refresh"),
        Binding("p", "providers", "Providers"),
        Binding("c", "close_mailbox", "Close"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.account: Account | None = None
        self.messages: list[Message] = []
        self.current_message: Message | None = None
        self.parsed: ParsedContent | None = None
        self.formatter = OutputFormatter(json_mode=False)

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Label("📬 Inbox", id="inbox-label")
                yield DataTable(id="inbox-table")
            with Vertical(id="main"):
                yield Label("📧 Message", id="message-label")
                with VerticalScroll(id="message-view"):
                    yield Label("Select a message to read", id="message-content")
        yield Label("Press 'n' new mailbox | 'w' watch | 'r' refresh | 'q' quit", id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        """Initialize on mount."""
        table = self.query_one("#inbox-table", DataTable)
        table.add_columns("From", "Subject", "Date")
        table.cursor_type = "row"

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
        self.query_one("#status-bar", Label).update(message)

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
        """Render inbox table."""
        table = self.query_one("#inbox-table", DataTable)
        table.clear()

        for msg in self.messages:
            date_str = msg.received_at.strftime("%H:%M")
            table.add_row(
                msg.from_address.split("@")[0],
                msg.subject[:30],
                date_str,
                key=msg.id,
            )

        self._update_status(f"Inbox: {len(self.messages)} messages")

    def _render_message(self, message: Message, parsed: ParsedContent) -> None:
        """Render message content."""
        content = self.query_one("#message-content", Label)

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

        content.update("\n".join(lines))

    @on(DataTable.RowSelected)
    def on_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle row selection in inbox."""
        if event.row_key is None:
            return

        msg_id = str(event.row_key.value)
        for msg in self.messages:
            if msg.id == msg_id:
                self.current_message = msg
                # Fetch full message
                self._fetch_message(msg.id)
                break

    @work(exclusive=True, thread=True)
    def _fetch_message(self, message_id: str) -> None:
        """Fetch full message in background."""
        if not self.account:
            return

        try:
            prov = resolve(self.account.provider)
            full_msg = prov.get_message(self.account, message_id)
            parsed = parse_message(full_msg)
            self.call_from_thread(self._render_message, full_msg, parsed)
        except TempMailError as e:
            self._update_status(f"Error fetching message: {e}")

    @work(exclusive=True, thread=True)
    def action_new_mailbox(self) -> None:
        """Create new mailbox."""
        self._update_status("Creating new mailbox...")

        try:
            # Use default provider
            prov = resolve()
            self.account = prov.create_account()
            save_session(self.account)
            self._update_status(f"Created: {self.account.address}")
            self._refresh_inbox()
        except TempMailError as e:
            self._update_status(f"Error: {e}")

    @work(exclusive=True, thread=True)
    def action_watch(self) -> None:
        """Watch for new emails."""
        if not self.account:
            self._update_status("No session. Press 'n' to create mailbox.")
            return

        self._update_status("Watching for new emails... (Ctrl+C to stop)")

        try:
            prov = resolve(self.account.provider)
            poller = Poller(prov, self.account, interval=3.0, timeout=60.0)
            message = poller.wait_for_message()
            parsed = parse_message(message)

            self.call_from_thread(self._render_message, message, parsed)
            self._update_status(f"New message from: {message.from_address}")

            # Refresh inbox
            self._refresh_inbox()
        except TempMailError as e:
            self._update_status(f"Watch stopped: {e}")
        except KeyboardInterrupt:
            self._update_status("Watch stopped by user")

    def action_refresh(self) -> None:
        """Refresh inbox."""
        self._refresh_inbox()

    def action_providers(self) -> None:
        """Show providers."""
        providers = list_providers()
        lines = ["Available providers:"]
        for name, cls in providers.items():
            online = "✓" if cls().health_check() else "✗"
            lines.append(f"  {online} {name}")
        self._update_status(" | ".join(lines))

    def action_close_mailbox(self) -> None:
        """Close current mailbox."""
        if not self.account:
            self._update_status("No active session.")
            return

        try:
            prov = resolve(self.account.provider)
            prov.delete_account(self.account)
            delete_session()
            self.account = None
            self.messages = []
            self.query_one("#inbox-table", DataTable).clear()
            self.query_one("#message-content", Label).update("No message selected")
            self._update_status("Mailbox closed.")
        except TempMailError as e:
            self._update_status(f"Error: {e}")


def main() -> None:
    """Run the TUI application."""
    app = TempMailTUI()
    app.run()


if __name__ == "__main__":
    main()
