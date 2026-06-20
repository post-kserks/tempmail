"""Exception hierarchy for TempMail CLI."""


class TempMailError(Exception):
    """Base exception for all TempMail errors."""

    def __init__(self, message: str, hint: str | None = None) -> None:
        super().__init__(message)
        self.hint = hint


class ProviderUnavailableError(TempMailError):
    """Raised when a mail provider is unreachable after retries."""


class RateLimitedError(TempMailError):
    """Raised when the provider returns 429."""


class AuthError(TempMailError):
    """Raised when authentication with the provider fails."""


class MessageNotFoundError(TempMailError):
    """Raised when a specific message cannot be found."""


class TimeoutWaitingForMailError(TempMailError):
    """Raised when watch timeout expires without receiving mail."""


class InvalidSessionError(TempMailError):
    """Raised when no active session exists for a command that requires one."""


class ConfigError(TempMailError):
    """Raised when configuration is invalid."""
