"""Output formatting — rich text and JSON modes."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from tempmail_cli.models import Account, Message, ParsedContent


def _json_serializer(obj: Any) -> str:
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


class OutputFormatter:
    """Renders output in text (rich) or JSON mode."""

    def __init__(self, json_mode: bool = False, color: bool = True) -> None:
        self._json = json_mode
        self._console = Console(highlight=False, no_markup=not color)

    def print_account_created(self, account: Account, session_path: str) -> None:
        if self._json:
            data = {
                "address": account.address,
                "provider": account.provider,
                "created_at": account.created_at.isoformat(),
            }
            self._console.print(json.dumps(data, default=_json_serializer))
        else:
            self._console.print(
                f"[green]✔[/green] Создан временный ящик: [bold]{account.address}[/bold]  "
                f"(провайдер: {account.provider})\n"
                f"  Сессия сохранена: {session_path}"
            )

    def print_message(self, message: Message, parsed: ParsedContent) -> None:
        if self._json:
            data = {
                "from": message.from_address,
                "subject": message.subject,
                "received_at": message.received_at.isoformat(),
                "best_code": parsed.best_code,
                "best_link": parsed.best_link,
                "all_codes": parsed.codes,
                "all_links": parsed.links,
            }
            self._console.print(json.dumps(data, default=_json_serializer))
        else:
            lines = [
                f"От:      {message.from_address}",
                f"Тема:    {message.subject}",
                f"Получено: {message.received_at.strftime('%Y-%m-%d %H:%M:%S')}",
            ]
            if parsed.best_code:
                lines.append(f"🔑 Вероятный код подтверждения: [bold]{parsed.best_code}[/bold]")
            if parsed.best_link:
                lines.append(f"🔗 Вероятная ссылка:\n   {parsed.best_link}")
            if len(parsed.codes) > 1:
                other = [c for c in parsed.codes if c != parsed.best_code]
                lines.append(f"Другие найденные коды: {', '.join(other)}")
            if len(parsed.links) > 1:
                other_links = [l for l in parsed.links if l != parsed.best_link]
                lines.append(f"Другие ссылки ({len(other_links)}): {', '.join(other_links[:3])}")

            content = "\n".join(lines)
            self._console.print(Panel(content, title="Новое письмо", border_style="green"))

    def print_inbox(self, messages: list[Message]) -> None:
        if self._json:
            data = [
                {
                    "id": m.id,
                    "from": m.from_address,
                    "subject": m.subject,
                    "received_at": m.received_at.isoformat(),
                    "seen": m.seen,
                }
                for m in messages
            ]
            self._console.print(json.dumps(data, default=_json_serializer))
        else:
            table = Table(title="Inbox")
            table.add_column("#", style="dim")
            table.add_column("From")
            table.add_column("Subject")
            table.add_column("Received")
            table.add_column("Read")
            for m in messages:
                table.add_row(
                    m.id,
                    m.from_address,
                    m.subject,
                    m.received_at.strftime("%Y-%m-%d %H:%M"),
                    "✔" if m.seen else "✗",
                )
            self._console.print(table)

    def print_providers(self, providers: dict[str, dict[str, Any]], default: str) -> None:
        if self._json:
            self._console.print(json.dumps(providers, default=_json_serializer))
        else:
            table = Table(title="Providers")
            table.add_column("NAME")
            table.add_column("STATUS")
            table.add_column("PUSH-SUPPORT")
            table.add_column("DEFAULT")
            for name, info in providers.items():
                status = "✔ online" if info.get("online") else "✗ offline"
                push = "yes" if info.get("supports_push") else "no"
                is_default = "*" if name == default else ""
                table.add_row(name, status, push, is_default)
            self._console.print(table)

    def print_error(self, message: str, hint: str | None = None) -> None:
        if self._json:
            data = {"error": message}
            if hint:
                data["hint"] = hint
            self._console.print(json.dumps(data))
        else:
            text = f"[red]✗[/red] {message}"
            if hint:
                text += f"\n[dim]{hint}[/dim]"
            self._console.print(text)

    def print_info(self, message: str) -> None:
        if self._json:
            self._console.print(json.dumps({"info": message}))
        else:
            self._console.print(f"[dim]{message}[/dim]")

    def print_clipboard_copy(self, content: str) -> None:
        if self._json:
            self._console.print(json.dumps({"copied": content}))
        else:
            self._console.print(f"[green]✔[/green] Скопировано в буфер обмена: {content}")
