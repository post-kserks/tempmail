#!/usr/bin/env python3
"""Demo script showing tempmail-cli usage."""

import subprocess
import sys
import json


def run(cmd: list[str]) -> tuple[int, str]:
    """Run a command and return exit code + output."""
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout + result.stderr


def main() -> None:
    print("=" * 50)
    print("  TempMail CLI Demo")
    print("=" * 50)

    # 1. Create mailbox
    print("\n[1] Создаю временный ящик...")
    code, output = run([sys.executable, "-m", "tempmail_cli", "new"])
    print(output)
    if code != 0:
        print("Ошибка создания ящика")
        sys.exit(1)

    # 2. List providers
    print("\n[2] Доступные провайдеры:")
    _, output = run([sys.executable, "-m", "tempmail_cli", "providers"])
    print(output)

    # 3. Check inbox
    print("\n[3] Проверяю инбокс...")
    _, output = run([sys.executable, "-m", "tempmail_cli", "inbox"])
    print(output)

    # 4. Show help for watch command
    print("\n[4] Команда watch:")
    _, output = run([sys.executable, "-m", "tempmail_cli", "watch", "--help"])
    print(output)

    print("=" * 50)
    print("  Готово! Теперь отправь письмо на указанный адрес")
    print("  и запусти: tempmail watch --copy")
    print("=" * 50)


if __name__ == "__main__":
    main()
