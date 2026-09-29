"""Domain errors. The API layer maps these to HTTP responses (Phase 7)."""


class AppError(Exception):
    """Base class for expected, handled application errors."""


class NotFoundError(AppError):
    """A requested entity does not exist."""


class ConflictError(AppError):
    """The operation conflicts with current state (bad transition, duplicate, etc.)."""
