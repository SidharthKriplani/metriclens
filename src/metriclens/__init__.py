"""MetricLens: metric movement decomposition for pandas DataFrames."""

from metriclens._version import __version__
from metriclens.core import MetricLens
from metriclens.exceptions import DecompositionTypeError, MetricLensError, ZeroDenominatorError
from metriclens.metrics import AverageMetric, CountMetric, MetricSpec, RatioMetric, SumMetric
from metriclens.report import AnalysisResult

__all__ = [
    "__version__",
    "MetricLens",
    "MetricSpec",
    "SumMetric",
    "CountMetric",
    "RatioMetric",
    "AverageMetric",
    "AnalysisResult",
    "MetricLensError",
    "ZeroDenominatorError",
    "DecompositionTypeError",
]
