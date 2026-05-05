class MetricLensError(Exception):
    """Base exception for MetricLens."""


class ZeroDenominatorError(MetricLensError):
    """Raised when a ratio metric has an impossible overall zero denominator."""


class DecompositionTypeError(MetricLensError):
    """Raised when a decomposition method is not valid for the metric type."""
