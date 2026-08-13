"""Application-specific exceptions with actionable messages."""


class TraceAIError(Exception):
    """Base class for expected application failures."""


class DataValidationError(TraceAIError):
    """Raised when an input dataset cannot satisfy the domain contract."""


class ArtifactNotFoundError(TraceAIError):
    """Raised when an engineering query references an unknown controlled ID."""
