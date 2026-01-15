"""Retry strategy with exponential backoff."""

import random
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Optional, TypeVar, cast


class RetryResult(Enum):
    """Result of a retry operation."""
    SUCCESS = "success"
    FAILURE = "failure"
    EXHAUSTED = "exhausted"


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    exponential_base: float = 2.0
    jitter: bool = True
    jitter_factor: float = 0.1


T = TypeVar('T')


class RetryStrategy:
    """Implements retry logic with exponential backoff."""

    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
        self._attempt = 0
        self._last_error: Optional[Exception] = None

    @property
    def attempt(self) -> int:
        """Current attempt number (1-indexed)."""
        return self._attempt

    @property
    def last_error(self) -> Optional[Exception]:
        """Last error encountered."""
        return self._last_error

    @property
    def should_retry(self) -> bool:
        """Check if more retries are available."""
        return self._attempt < self.config.max_attempts

    def get_delay(self, attempt: Optional[int] = None) -> float:
        """Calculate delay for the given attempt using exponential backoff."""
        attempt = attempt or self._attempt

        # Exponential backoff
        delay = self.config.base_delay * (self.config.exponential_base ** (attempt - 1))

        # Cap at max delay
        delay = min(delay, self.config.max_delay)

        # Add jitter
        if self.config.jitter:
            jitter_range = delay * self.config.jitter_factor
            delay += random.uniform(-jitter_range, jitter_range)

        return max(0, delay)

    def reset(self) -> None:
        """Reset the retry state."""
        self._attempt = 0
        self._last_error = None

    def record_attempt(self, success: bool = False, error: Optional[Exception] = None) -> None:
        """Record an attempt result."""
        self._attempt += 1
        if error:
            self._last_error = error

    def wait(self) -> None:
        """Wait for the appropriate backoff duration."""
        if self._attempt > 0:
            delay = self.get_delay()
            time.sleep(delay)

    def execute(
        self,
        func: Callable[[], T],
        on_retry: Optional[Callable[[int, Exception], None]] = None,
        should_retry: Optional[Callable[[Exception], bool]] = None,
    ) -> tuple[RetryResult, Optional[T], Optional[Exception]]:
        """
        Execute a function with retry logic.

        Args:
            func: Function to execute
            on_retry: Optional callback called before each retry
            should_retry: Optional predicate to determine if exception is retryable

        Returns:
            Tuple of (result_status, return_value, last_exception)
        """
        self.reset()

        while self._attempt < self.config.max_attempts:
            self._attempt += 1

            try:
                result = func()
                return (RetryResult.SUCCESS, result, None)

            except Exception as e:
                self._last_error = e

                # Check if we should retry this exception
                if should_retry and not should_retry(e):
                    return (RetryResult.FAILURE, None, e)

                # Check if more attempts available
                if self._attempt >= self.config.max_attempts:
                    return (RetryResult.EXHAUSTED, None, e)

                # Call retry callback
                if on_retry:
                    on_retry(self._attempt, e)

                # Wait before retry
                self.wait()

        return (RetryResult.EXHAUSTED, None, self._last_error)


class RetryableError(Exception):
    """Error that should be retried."""
    pass


class NonRetryableError(Exception):
    """Error that should not be retried."""
    pass


def with_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
) -> Callable:
    """Decorator to add retry logic to a function."""

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        def wrapper(*args: Any, **kwargs: Any) -> T:
            config = RetryConfig(
                max_attempts=max_attempts,
                base_delay=base_delay,
                max_delay=max_delay,
            )
            strategy = RetryStrategy(config)

            result, value, error = strategy.execute(lambda: func(*args, **kwargs))

            if result == RetryResult.SUCCESS:
                return cast(T, value)
            else:
                raise error or Exception("Retry exhausted with no error")

        return wrapper
    return decorator
