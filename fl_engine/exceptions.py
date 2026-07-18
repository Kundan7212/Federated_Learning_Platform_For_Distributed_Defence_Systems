class TrainingCancelledError(Exception):
    """Raised when a training run is cancelled. Shared by the FL engine and backend for consistent cancellation handling."""

