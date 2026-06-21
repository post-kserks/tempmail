"""CLI application — typer commands for TempMail."""

from __future__ import annotations

import logging
import sys
from typing import Any

import typer

from tempmail_cli import __version__
from tempmail_cli.clipboard import copy_to_clipboard
from tempmail_cli.config import load_config
from tempmail_cli.exceptions import TempMailError
from tempmail_cli.output import OutputFormatter
from tempmail_cli.parser import parse_message
from tempmail_cli.poller import Poller
from tempmail_cli.provider_manager import list_providers, resolve
from tempmail_cli.session_store import delete_session, load_session, save_session

app = typer.Typer(name="tempmail", help="Temporary email CLI tool")

# Global options
_provider_opt = typer.Option(None, "--provider", help="Mail provider (mailtm, guerrilla)")
_json_opt = typer.Option(False, "--json", help="Machine-readable JSON output")
_session_name_opt = typer.Option("default", "--session-name", help="Named session")
_verbose_opt = typer.Option(False, "--verbose", "-v", help="Verbose output")
_debug_opt = typer.Option(False, "--debug", help="Full debug output with traces")
_no_color_opt = typer.Option(False, "--no-color", help="Disable colored output")


def _setup_logging(verbose: bool, debug: bool) -> None:
    level = logging.WARNING
    if debug:
        level = logging.DEBUG
    elif verbose:
        level = logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
        stream=sys.stderr,
    )


def _get_formatter(json_mode: bool, no_color: bool) -> OutputFormatter:
    return OutputFormatter(json_mode=json_mode, color=not no_color)


@app.command()
def new(
    provider: str | None = _provider_opt,
    domain: str | None = typer.Option(None, "--domain", help="Specific domain"),
    username: str | None = typer.Option(None, "--username", help="Custom username"),
    json_mode: bool = _json_opt,
    session_name: str = _session_name_opt,
    verbose: bool = _verbose_opt,
    debug: bool = _debug_opt,
    no_color: bool = _no_color_opt,
) -> None:
    """Create a new temporary mailbox."""
    _setup_logging(verbose, debug)
    fmt = _get_formatter(json_mode, no_color)

    try:
        prov = resolve(provider)
        account = prov.create_account(domain=domain, username=username)
        path = save_session(account, session_name)
        fmt.print_account_created(account, str(path))
    except TempMailError as e:
        fmt.print_error(str(e), e.hint)
        raise typer.Exit(1)


@app.command()
def watch(
    provider: str | None = _provider_opt,
    interval: float = typer.Option(3.0, "--interval", help="Poll interval in seconds"),
    timeout: float = typer.Option(120.0, "--timeout", help="Max wait time in seconds"),
    from_contains: str | None = typer.Option(None, "--from", help="Filter by sender"),
    subject_contains: str | None = typer.Option(
        None, "--subject-contains", help="Filter by subject"
    ),
    copy: bool = typer.Option(False, "--copy", help="Copy code/link to clipboard"),
    session_name: str = _session_name_opt,
    json_mode: bool = _json_opt,
    verbose: bool = _verbose_opt,
    debug: bool = _debug_opt,
    no_color: bool = _no_color_opt,
) -> None:
    """Wait for and display an incoming email."""
    _setup_logging(verbose, debug)
    fmt = _get_formatter(json_mode, no_color)

    try:
        account = load_session(session_name)
        prov = resolve(provider or account.provider)
        poller = Poller(prov, account, interval=interval, timeout=timeout)
        message = poller.wait_for_message(
            from_contains=from_contains, subject_contains=subject_contains
        )
        parsed = parse_message(message)
        fmt.print_message(message, parsed)

        if copy:
            clip_text = parsed.best_code or parsed.best_link
            if clip_text and copy_to_clipboard(clip_text):
                fmt.print_clipboard_copy(clip_text)
    except KeyboardInterrupt:
        fmt.print_info("Ожидание прервано пользователем")
        raise typer.Exit(130)
    except TempMailError as e:
        fmt.print_error(str(e), e.hint)
        raise typer.Exit(1)


@app.command()
def inbox(
    provider: str | None = _provider_opt,
    limit: int = typer.Option(20, "--limit", help="Max messages to show"),
    session_name: str = _session_name_opt,
    json_mode: bool = _json_opt,
    verbose: bool = _verbose_opt,
    debug: bool = _debug_opt,
    no_color: bool = _no_color_opt,
) -> None:
    """Show inbox messages."""
    _setup_logging(verbose, debug)
    fmt = _get_formatter(json_mode, no_color)

    try:
        account = load_session(session_name)
        prov = resolve(provider or account.provider)
        messages = prov.list_messages(account)
        fmt.print_inbox(messages[:limit])
    except TempMailError as e:
        fmt.print_error(str(e), e.hint)
        raise typer.Exit(1)


@app.command()
def read(
    message_id: str = typer.Argument(..., help="Message ID to read"),
    provider: str | None = _provider_opt,
    copy: bool = typer.Option(False, "--copy", help="Copy code/link to clipboard"),
    raw: bool = typer.Option(False, "--raw", help="Show raw HTML/text"),
    session_name: str = _session_name_opt,
    json_mode: bool = _json_opt,
    verbose: bool = _verbose_opt,
    debug: bool = _debug_opt,
    no_color: bool = _no_color_opt,
) -> None:
    """Read a specific message by ID."""
    _setup_logging(verbose, debug)
    fmt = _get_formatter(json_mode, no_color)

    try:
        account = load_session(session_name)
        prov = resolve(provider or account.provider)
        message = prov.get_message(account, message_id)

        if raw:
            content = message.html_body or message.text_body or "(empty)"
            fmt.print_raw(content, json_mode)
            return

        parsed = parse_message(message)
        fmt.print_message(message, parsed)

        if copy:
            clip_text = parsed.best_code or parsed.best_link
            if clip_text and copy_to_clipboard(clip_text):
                fmt.print_clipboard_copy(clip_text)
    except TempMailError as e:
        fmt.print_error(str(e), e.hint)
        raise typer.Exit(1)



@app.command()
def providers(
    json_mode: bool = _json_opt,
    no_color: bool = _no_color_opt,
) -> None:
    """Show available mail providers."""
    fmt = _get_formatter(json_mode, no_color)
    cfg = load_config()

    result: dict[str, Any] = {}
    for name, cls in list_providers().items():
        try:
            p = cls()
            online = p.health_check()
        except Exception:
            online = False
        result[name] = {
            "online": online,
            "supports_push": cls.supports_push,
        }

    fmt.print_providers(result, cfg.default_provider)


@app.command()
def close(
    provider: str | None = _provider_opt,
    session_name: str = _session_name_opt,
    json_mode: bool = _json_opt,
    verbose: bool = _verbose_opt,
    debug: bool = _debug_opt,
    no_color: bool = _no_color_opt,
) -> None:
    """Close active session and delete the temporary mailbox."""
    _setup_logging(verbose, debug)
    fmt = _get_formatter(json_mode, no_color)

    try:
        account = load_session(session_name)
        prov = resolve(provider or account.provider)
        prov.delete_account(account)
        delete_session(session_name)
        fmt.print_info("Сессия закрыта, ящик удалён.")
    except TempMailError as e:
        fmt.print_error(str(e), e.hint)
        raise typer.Exit(1)


@app.command()
def tui() -> None:
    """Launch interactive TUI interface."""
    from tempmail_cli.tui import main as tui_main

    tui_main()


@app.callback(invoke_without_command=True)
def main(
    version: bool = typer.Option(False, "--version", "-V", help="Show version"),
) -> None:
    """TempMail CLI — temporary email generator with verification code extraction."""
    if version:
        typer.echo(f"tempmail {__version__}")
        raise typer.Exit()


if __name__ == "__main__":
    app()
