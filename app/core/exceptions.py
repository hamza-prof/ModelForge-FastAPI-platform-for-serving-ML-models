"""
Custom exception hierarchy for the ML Platform.

Usage:
    - Services raise these exceptions for business logic errors.
    - A global exception handler in main.py converts them to HTTP responses.
"""


class MLPlatformError(Exception):
    """Base exception for all application errors."""

    def __init__(self, detail: str = "An unexpected error occurred"):
        self.detail = detail
        super().__init__(self.detail)


class NotFoundError(MLPlatformError):
    """Raised when a requested resource does not exist."""

    def __init__(self, resource: str, identifier: str):
        super().__init__(f"{resource} with id '{identifier}' not found")


class AlreadyExistsError(MLPlatformError):
    """Raised when attempting to create a resource that already exists."""

    def __init__(self, resource: str, field: str, value: str):
        super().__init__(f"{resource} with {field} '{value}' already exists")


class AuthenticationError(MLPlatformError):
    """Raised when authentication fails (bad credentials, expired token)."""

    def __init__(self, detail: str = "Invalid credentials"):
        super().__init__(detail)


class AuthorizationError(MLPlatformError):
    """Raised when an authenticated user lacks permission."""

    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(detail)


class ValidationError(MLPlatformError):
    """Raised when input data fails business-level validation."""

    def __init__(self, detail: str):
        super().__init__(detail)


class ModelLoadError(MLPlatformError):
    """Raised when an ML model file cannot be loaded or deserialized."""

    def __init__(self, model_name: str, reason: str):
        super().__init__(f"Failed to load model '{model_name}': {reason}")
