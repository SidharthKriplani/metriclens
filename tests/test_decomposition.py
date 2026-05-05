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


# ── edge case tests ───────────────────────────────────────────────────────────

def test_negative_delta_direction_is_down():
    """Revenue that decreases produces a DOWN direction summary."""
    df = pd.DataFrame(
        [
            {"date": "2026-01-01", "channel": "a", "revenue": 1000},
            {"date": "2026-01-02", "channel": "a", "revenue": 800},
        ]
    )
    lens = MetricLens(df, "date", ("2026-01-01", "2026-01-01"), ("2026-01-02", "2026-01-02"), ["channel"])
    assert lens.analyze(SumMetric("revenue")).summary()["direction"] == "DOWN"


def test_absolute_delta_sign_matches_direction():
    """absolute_delta is negative when direction is DOWN."""
    df = pd.DataFrame(
        [
            {"date": "2026-01-01", "channel": "a", "revenue": 500},
            {"date": "2026-01-02", "channel": "a", "revenue": 300},
        ]
    )
    lens = MetricLens(df, "date", ("2026-01-01", "2026-01-01"), ("2026-01-02", "2026-01-02"), ["channel"])
    summary = lens.analyze(SumMetric("revenue")).summary()
    assert summary["absolute_delta"] == pytest.approx(-200.0)
    assert summary["direction"] == "DOWN"


def test_multi_dimension_analysis_returns_one_entry_per_dimension():
    """Analyzing with two dimensions returns two entries in the dimensions list."""
    lens = MetricLens(base_df(), "date", ("2026-01-01", "2026-01-01"), ("2026-01-02", "2026-01-02"),
                      ["channel", "device"])
    result = lens.analyze(SumMetric("revenue"))
    assert len(result.to_dict()["dimensions"]) == 2


# ── cross-dimension interaction tests ────────────────────────────────────────

def test_cross_dimension_returns_expected_keys():
    """analyze_cross_dimensions result includes dim1, dim2, cross_label, top_interactions."""
    lens = MetricLens(base_df(), "date", ("2026-01-01", "2026-01-01"), ("2026-01-02", "2026-01-02"),
                      ["channel", "device"])
    cross = lens.analyze_cross_dimensions(SumMetric("revenue"), "channel", "device")
    for key in ("dim1", "dim2", "cross_label", "total_cells", "top_interactions", "all_interactions"):
        assert key in cross


def test_cross_dimension_cells_span_product():
    """Number of interaction cells equals len(channels) × len(devices) in the data."""
    lens = MetricLens(base_df(), "date", ("2026-01-01", "2026-01-01"), ("2026-01-02", "2026-01-02"),
                      ["channel", "device"])
    cross = lens.analyze_cross_dimensions(SumMetric("revenue"), "channel", "device")
    # base_df has 2 channels (a, b) × 2 devices (mobile, desktop) = 4 cells
    assert cross["total_cells"] == 4


def test_cross_dimension_interaction_present_in_analyze_payload():
    """analyze() auto-populates cross_dimension_interactions when ≥2 dimensions."""
    lens = MetricLens(base_df(), "date", ("2026-01-01", "2026-01-01"), ("2026-01-02", "2026-01-02"),
                      ["channel", "device"])
    result = lens.analyze(SumMetric("revenue"))
    cross = result.cross_dimension_interactions()
    assert cross is not None
    assert cross["dim1"] == "channel"
    assert cross["dim2"] == "device"


def test_cross_dimension_not_present_for_single_dimension():
    """analyze() leaves cross_dimension_interactions None when only 1 dimension."""
    df = pd.DataFrame([
        {"date": "2026-01-01", "channel": "a", "revenue": 1000},
        {"date": "2026-01-02", "channel": "a", "revenue": 1200},
    ])
    lens = MetricLens(df, "date", ("2026-01-01", "2026-01-01"), ("2026-01-02", "2026-01-02"),
                      ["channel"])
    result = lens.analyze(SumMetric("revenue"))
    assert result.cross_dimension_interactions() is None


def test_cross_dimension_invalid_dim_raises():
    """analyze_cross_dimensions raises ValueError for a missing dimension column."""
    lens = MetricLens(base_df(), "date", ("2026-01-01", "2026-01-01"), ("2026-01-02", "2026-01-02"),
                      ["channel", "device"])
    with pytest.raises(ValueError):
        lens.analyze_cross_dimensions(SumMetric("revenue"), "channel", "nonexistent_col")
