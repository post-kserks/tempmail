# TempMail CLI

Консольный инструмент для создания временных email-адресов с автоматическим извлечением кодов подтверждения.

## Установка

```bash
pip install tempmail-cli
# или
pipx install tempmail-cli
```

## Быстрый старт

```bash
# Создать временный ящик
tempmail new

# Ждать письмо и скопировать код
tempmail watch --copy

# Или использовать TUI
tempmail tui
```

## Команды

| Команда | Описание |
|---------|----------|
| `tempmail new` | Создать новый временный ящик |
| `tempmail watch` | Ждать входящее письмо |
| `tempmail inbox` | Показать список писем |
| `tempmail read <id>` | Прочитать конкретное письмо |
| `tempmail providers` | Список доступных провайдеров |
| `tempmail close` | Закрыть сессию и удалить ящик |
| `tempmail tui` | Интерактивный интерфейс |

## Провайдеры

| Провайдер | Описание |
|-----------|----------|
| `mailtm` | По умолчанию, бесплатный |
| `guerrilla` | Альтернативный провайдер |
| `tempmail-lol` | Дополнительный провайдер |

## Глобальные флаги

| Флаг | Описание |
|------|----------|
| `--provider` | Выбрать провайдер (mailtm, guerrilla) |
| `--json` | Машиночитаемый вывод |
| `--session-name` | Именованная сессия |
| `--verbose` / `-v` | Подробный вывод |
| `--debug` | Полный вывод с трейсбеками |

## Примеры

```bash
# Быстрый сценарий
tempmail new
tempmail watch --copy

# Ожидание от конкретного отправителя
tempmail watch --from "github.com" --timeout 300

# Использовать Guerrilla Mail
tempmail new --provider guerrilla

# Машиночитаемый вывод
CODE=$(tempmail watch --json --timeout 60 | jq -r '.best_code')

# Несколько параллельных ящиков
tempmail new --session-name acc1
tempmail new --session-name acc2
tempmail watch --session-name acc1
```

## TUI (интерактивный интерфейс)

```bash
tempmail tui
```

### Управление в TUI

| Клавиша | Действие |
|---------|----------|
| `↑↓` | Навигация по инбоксу |
| `Enter` | Открыть сообщение |
| `y` | Копировать адрес почты |
| `o` | Копировать код подтверждения |
| `m` | Копировать сообщение |
| `n` | Создать новый ящик |
| `w` | Watch (ожидание письма) |
| `r` | Обновить инбокс |
| `q` | Выход |

### Выделение текста

В TUI можно выделять текст мышью и копировать через `Cmd+C` (macOS) или `Ctrl+Shift+C` (Linux).

## Конфигурация

Файл: `~/.config/tempmail-cli/config.yaml`

```yaml
default_provider: mailtm
providers:
  mailtm:
    base_url: "https://api.mail.tm"
    requests_per_second: 6
  guerrilla:
    base_url: "https://api.guerrillamail.com/ajax.php"
    requests_per_second: 0.5
defaults:
  interval: 3
  timeout: 120
output:
  color: true
```

### Переменные окружения

| Переменная | Описание |
|------------|----------|
| `TEMPMAIL_PROVIDER` | Провайдер по умолчанию |
| `TEMPMAIL_TIMEOUT` | Таймаут ожидания |
| `TEMPMAIL_INTERVAL` | Интервал опроса |
| `TEMPMAIL_NO_COLOR` | Отключить цвета |

## Архитектура

```
CLI (typer) → Provider Manager → Providers (mail.tm, Guerrilla, tempmail-lol)
                    ↓
               Session Store (JSON)
                    ↓
               Message Parser (BeautifulSoup + regex)
                    ↓
               Output Formatter (rich / JSON)
```

### Ключевые принципы

- **Provider Abstraction** — все сервисы почты реализуют единый интерфейс `MailProvider`
- **Изоляция I/O** — парсер и модели не зависят от сети
- **Fail-soft** — недоступные провайдеры предлагают альтернативы

## Тестирование

```bash
# Запуск тестов
pytest

# С покрытием
pytest --cov=tempmail_cli

# Линтер
ruff check src/ tests/

# Типизация
mypy src/tempmail_cli/
```

## Предупреждение о приватности

⚠️ Временная почта — это публичный сервис. **Не используйте** для писем с конфиденциальными данными. Переписка не приватна по дизайну сторонних провайдеров.

## Лицензия

MIT
