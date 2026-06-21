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
# Запустить интерактивный интерфейс
./run.sh tui

# Создать временный ящик
./run.sh new

# Ждать письмо и скопировать код
./run.sh watch --copy
```

### Установка через pip

```bash
pip install tempmail-cli
# или
pipx install tempmail-cli

# Затем использовать команды напрямую
tempmail tui
tempmail new
tempmail watch --copy
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
./run.sh new
./run.sh watch --copy

# Ожидание от конкретного отправителя
./run.sh watch --from "github.com" --timeout 300

# Использовать Guerrilla Mail
./run.sh new --provider guerrilla

# Машиночитаемый вывод
CODE=$(./run.sh watch --json --timeout 60 | jq -r '.best_code')

# Несколько параллельных ящиков
./run.sh new --session-name acc1
./run.sh new --session-name acc2
./run.sh watch --session-name acc1
```

## TUI (интерактивный интерфейс)

```bash
./run.sh tui
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

## Примеры использования

### Регистрация на сервисе

```bash
# 1. Создаём временный ящик
./run.sh new
# ✔ Создан временный ящик: abc123@mail.tm

# 2. Используем адрес для регистрации
# Скопируйте адрес и вставьте в форму регистрации

# 3. Ждём письмо с кодом подтверждения
./run.sh watch --from "github.com" --copy
# ✔ Код 482913 скопирован в буфер обмена!

# 4. Вставляем код в форму регистрации
```

### Быстрое получение кода

```bash
# Создать ящик и сразу ждать письмо
./run.sh new && ./run.sh watch --copy
```

### Работа с конкретным сервисом

```bash
# Ожидание письма от GitHub
./run.sh watch --from "github.com" --timeout 300

# Ожидание письма от Google
./run.sh watch --from "google.com" --subject-contains "verify"

# Ожидание письма от Slack
./run.sh watch --from "slack.com" --subject-contains "confirm"
```

### Использование в скриптах

```bash
# Получить код в переменную
CODE=$(./run.sh watch --json --timeout 60 | jq -r '.best_code')
echo "Код подтверждения: $CODE"

# Проверить инбокс
./run.sh inbox --json | jq '.[].subject'

# Прочитать конкретное письмо
./run.sh read 12345 --json | jq '.best_code'
```

### Несколько параллельных ящиков

```bash
# Создать несколько ящиков
./run.sh new --session-name work
./run.sh new --session-name personal

# Проверить инбокс рабочего ящика
./run.sh inbox --session-name work

# Ждать письмо в личном ящике
./run.sh watch --session-name personal --copy

# Закрыть рабочий ящик
./run.sh close --session-name work
```

### Использование разных провайдеров

```bash
# Использовать Guerrilla Mail
./run.sh new --provider guerrilla
./run.sh watch --copy

# Проверить доступные провайдеры
./run.sh providers
```

### Отладка

```bash
# Подробный вывод
./run.sh new --verbose

# Полный debug с трейсбеками
./run.sh watch --debug

# Просмотр логов
TEMPMAIL_LOG_FILE=/tmp/tempmail.log ./run.sh watch
```

### TUI — интерактивный режим

```bash
# Запустить TUI
./run.sh tui

# Управление:
# ↑↓     - навигация по инбоксу
# Enter  - открыть сообщение
# y      - копировать адрес почты
# o      - копировать код подтверждения
# m      - копировать сообщение
# n      - создать новый ящик
# w      - watch (ожидание письма)
# r      - обновить инбокс
# q      - выход

# Выделение текста мышью + Cmd+C для копирования
```
