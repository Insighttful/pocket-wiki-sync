"""Custom exceptions for HeyPocket API."""


class HeyPocketError(Exception):
    """Base exception for HeyPocket API errors."""

    pass


class APIError(HeyPocketError):
    """API request failed."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class DownloadError(HeyPocketError):
    """Failed to download recording or transcript."""

    pass


class RateLimitError(HeyPocketError):
    """Rate limit exceeded."""

    def __init__(self, message: str, retry_after: int | None = None):
        super().__init__(message)
        self.retry_after = retry_after


class AuthenticationError(HeyPocketError):
    """Authentication failed."""

    pass


class NotFoundError(HeyPocketError):
    """Resource not found."""

    pass


class ValidationError(HeyPocketError):
    """Invalid input or parameters."""

    pass
