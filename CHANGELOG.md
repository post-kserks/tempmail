# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-06-21

## [0.1.0] - 2026-06-21

## [0.1.0] - 2026-06-21

## [0.1.0] - 2026-06-21

## [0.1.0] - 2026-06-21

## [0.1.0] - 2026-06-21

### Added
- TUI interface with Textual for interactive email management
- Text selection support in TUI (click and drag + Cmd+C)
- Multiple provider support: mail.tm, Guerrilla Mail, TempMail.lol
- Verification code extraction from emails
- Confirmation link detection
- Session management with named sessions
- JSON output mode for scripts
- Clipboard integration with --copy flag

### Fixed
- Mail.tm authentication with lowercase address
- Guerrilla Mail date parsing
- Thread safety for signal handlers
- Error handling for API responses

## [0.1.0] - 2026-06-21

### Added
- Initial release
- Basic CLI commands: new, watch, inbox, read, providers, close
- Mail.tm provider implementation
- Email parsing with code and link extraction
- Session persistence with file permissions 600
- Rate limiting for API calls
- Rich text and JSON output formatting
