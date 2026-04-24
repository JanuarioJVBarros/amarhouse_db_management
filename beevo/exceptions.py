class BeevoError(Exception):
    """Base exception for Beevo integration failures."""


class BeevoConfigurationError(BeevoError):
    """Raised when required Beevo configuration is missing or invalid."""


class BeevoTransportError(BeevoError):
    """Raised when the HTTP transport layer fails."""


class BeevoResponseError(BeevoError):
    """Raised when Beevo returns an unexpected HTTP or GraphQL response."""


class BeevoValidationError(BeevoError):
    """Raised when expected response data is missing or malformed."""
