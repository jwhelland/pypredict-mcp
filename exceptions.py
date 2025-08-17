"""Custom exceptions for the pypredict-mcp project."""

class PypredictMcpError(Exception):
    """Base exception class for this project."""
    pass

class APIError(PypredictMcpError):
    """Raised when an API call fails."""
    pass

class NoDataFoundError(PypredictMcpError):
    """Raised when an API call returns no data."""
    pass

class ConfigurationError(PypredictMcpError):
    """Raised for configuration-related errors."""
    pass
