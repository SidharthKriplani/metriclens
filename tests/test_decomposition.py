import pandas as pd
import pytest

from metriclens import DecompositionTypeError, MetricLens, RatioMetric, SumMetric


def base_df():
    return pd.DataFrame(
        [
            {"date": "2026-01-01", "channel": "a", "device": "mobile", "orders": 10, "sessions": 100, "revenue": 1000},
            {"date": "2026-01-01", "channel": "b", "device": "desktop", "orders": 10, "sessions": 100, "revenue": 2000},
            {"date": "2026-01-02", "channel": "a", "device": "mobile", "orders": 8, "sessions": 100, "revenue": 900},
            {"date": "2026-01-02", "channel": "b", "device": "desktop", "orders": 15, "sessions": 100, "revenue": 2500},
        ]
    )


def test_ratio_identity_residual_is_near_zero():
    lens = MetricLens(base_df(), "date", ("2026-01-01", "2026-01-01"), ("2026-01-02", "2026-01-02"), ["channel"])
    result = lens.analyze(RatioMetric("orders", "sessions", name="cvr"))
    residual = result.to_dict()["dimensions"][0]["identity_residual"]
    assert residual == pytest.approx(0.0)


def test_additive_contributions_sum_to_total_delta():
    lens = MetricLens(base_df(), "date", ("2026-01-01", "2026-01-01"), ("2026-01-02", "2026-01-02"), ["channel"])
    result = lens.analyze(SumMetric("revenue"))
    rows = result.to_dict()["dimensions"][0]["segment_contributions"]
    assert sum(r["segment_delta"] for r in rows) == pytest.approx(400)


def test_flat_case_contribution_pct_is_none():
    df = pd.DataFrame(
        [
            {"date": "2026-01-01", "channel": "a", "orders": 10, "sessions": 100, "revenue": 1000},
            {"date": "2026-01-02", "channel": "a", "orders": 10, "sessions": 100, "revenue": 1000},
        ]
    )
    lens = MetricLens(df, "date", ("2026-01-01", "2026-01-01"), ("2026-01-02", "2026-01-02"), ["channel"])
    result = lens.analyze(SumMetric("revenue"))
    rows = result.to_dict()["dimensions"][0]["segment_contributions"]
    assert rows[0]["contribution_pct"] is None
    assert result.summary()["direction"] == "FLAT"


def test_zero_baseline_relative_delta_is_none():
    df = pd.DataFrame(
        [
            {"date": "2026-01-01", "channel": "a", "revenue": 0},
            {"date": "2026-01-02", "channel": "a", "revenue": 10},
        ]
    )
    lens = MetricLens(df, "date", ("2026-01-01", "2026-01-01"), ("2026-01-02", "2026-01-02"), ["channel"])
    assert lens.analyze(SumMetric("revenue")).summary()["relative_delta_pct"] is None


def test_new_and_disappeared_segments():
    df = pd.DataFrame(
        [
            {"date": "2026-01-01", "channel": "old", "revenue": 10},
            {"date": "2026-01-02", "channel": "new", "revenue": 20},
        ]
    )
    lens = MetricLens(df, "date", ("2026-01-01", "2026-01-01"), ("2026-01-02", "2026-01-02"), ["channel"])
    statuses = {r["segment"]: r["segment_status"] for r in lens.analyze(SumMetric("revenue")).to_dict()["dimensions"][0]["segment_contributions"]}
    assert statuses["old"] == "disappeared"
    assert statuses["new"] == "new"


def test_disappeared_segment_cross_term_positive_under_zero_fill():
    df = pd.DataFrame(
        [
            {"date": "2026-01-01", "channel": "gone", "orders": 5, "sessions": 100},
            {"date": "2026-01-01", "channel": "stay", "orders": 5, "sessions": 100},
            {"date": "2026-01-02", "channel": "stay", "orders": 5, "sessions": 100},
        ]
    )
    lens = MetricLens(df, "date", ("2026-01-01", "2026-01-01"), ("2026-01-02", "2026-01-02"), ["channel"])
    rows = lens.analyze(RatioMetric("orders", "sessions", name="cvr")).to_dict()["dimensions"][0]["segment_contributions"]
    gone = next(r for r in rows if r["segment"] == "gone")
    assert gone["segment_status"] == "disappeared"
    assert gone["cross_term"] > 0


def test_mix_shift_raises_for_additive_metric():
    lens = MetricLens(base_df(), "date", ("2026-01-01", "2026-01-01"), ("2026-01-02", "2026-01-02"), ["channel"])
    result = lens.analyze(SumMetric("revenue"))
    with pytest.raises(DecompositionTypeError):
        result.mix_shift()
