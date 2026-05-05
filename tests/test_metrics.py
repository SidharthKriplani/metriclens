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


# ── edge case tests ───────────────────────────────────────────────────────────

def test_sum_metric_all_null_returns_zero():
    """SumMetric on an all-NaN column returns 0 (pandas sum skips NaN by default)."""
    df = pd.DataFrame({"revenue": [None, None, None]}, dtype=float)
    assert SumMetric("revenue").compute(df) == 0.0


def test_sum_metric_negative_values():
    """SumMetric handles negative values correctly."""
    df = pd.DataFrame({"revenue": [-10, 20, -5]})
    assert SumMetric("revenue").compute(df) == pytest.approx(5.0)


def test_count_metric_all_null_column_returns_zero():
    """CountMetric on a column where every value is null returns 0."""
    df = pd.DataFrame({"x": [None, None, None]})
    assert CountMetric("x").compute(df) == 0


def test_ratio_metric_null_numerator_treated_as_zero():
    """NaN in numerator column is treated as 0 by pandas sum, so ratio is 0."""
    df = pd.DataFrame({"orders": [None, None], "sessions": [100, 100]}, dtype=float)
    assert RatioMetric("orders", "sessions").compute(df) == pytest.approx(0.0)


def test_average_metric_zero_weight_raises():
    """AverageMetric with all-zero weights raises ZeroDenominatorError."""
    df = pd.DataFrame({"value": [10, 20], "weight": [0, 0]})
    with pytest.raises(ZeroDenominatorError):
        AverageMetric("value", "weight").compute(df)


def test_average_metric_empty_df_raises():
    """AverageMetric on empty DataFrame raises ZeroDenominatorError."""
    df = pd.DataFrame({"value": []})
    with pytest.raises(ZeroDenominatorError):
        AverageMetric("value").compute(df)
