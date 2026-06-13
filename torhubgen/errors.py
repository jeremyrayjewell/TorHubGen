"""Project-local exceptions."""


class ShutdownRequested(Exception):
    """Raised when the appliance should stop cleanly."""


class StemDependencyMissing(RuntimeError):
    """Raised when the optional Stem dependency is unavailable."""
