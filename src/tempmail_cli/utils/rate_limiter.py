"""Simple token-bucket rate limiter."""

import time
import threading


class RateLimiter:
    """Token-bucket rate limiter for API calls."""

    def __init__(self, requests_per_second: float) -> None:
        self._min_interval = 1.0 / requests_per_second if requests_per_second > 0 else 0
        self._last_call = 0.0
        self._lock = threading.Lock()

    def wait(self) -> None:
        """Block until a request can be made without exceeding the rate limit."""
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_call
            if elapsed < self._min_interval:
                time.sleep(self._min_interval - elapsed)
            self._last_call = time.monotonic()
