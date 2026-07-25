"""Project-specific exceptions."""


class DebtInterestError(Exception):
    """Base exception for the project."""


class SourceError(DebtInterestError):
    """Raised when an upstream source cannot be fetched or parsed."""


class ValidationError(DebtInterestError):
    """Raised when mandatory validation rules fail."""
