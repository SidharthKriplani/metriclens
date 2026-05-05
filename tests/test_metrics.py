import pandas as pd
import pytest

from metriclens import AverageMetric, CountMetric, RatioMetric, SumMetric, ZeroDenominatorError


def test_sum_metric_compute():
    df = pd.DataFrame({"revenue": [10, 20, 30]})
    assert SumMetric("revenue").compute(df) == 60


def test_count_metric_compute_rows():
    df = pd.DataFrame({"x": [1, None, 3]})
    assert CountMetric().compute(df) == 3


def test_count_metric_compute_non_null_column():
    df = pd.DataFrame({"x": [1, None, 3]})
    assert CountMetric("x").compute(df) == 2


def test_ratio_metric_compute():
    df = pd.DataFrame({"orders": [2, 3], "sessions": [20, 30]})
    assert RatioMetric("orders", "sessions").compute(df) == pytest.approx(0.1)


def test_ratio_zero_denominator_raises():
    df = pd.DataFrame({"orders": [2, 3], "sessions": [0, 0]})
    with pytest.raises(ZeroDenominatorError):
        RatioMetric("orders", "sessions").compute(df)


def test_average_metric_compute_unweighted():
    df = pd.DataFrame({"value": [10, 20, 30]})
    assert AverageMetric("value").compute(df) == 20


def test_average_metric_compute_weighted():
    df = pd.DataFrame({"value": [10, 20], "weight": [1, 3]})
    assert AverageMetric("value", "weight").compute(df) == pytest.approx(17.5)
