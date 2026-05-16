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
    """Number of interaction cells equals the unique channel/device combos actually present."""
    lens = MetricLens(base_df(), "date", ("2026-01-01", "2026-01-01"), ("2026-01-02", "2026-01-02"),
                      ["channel", "device"])
    cross = lens.analyze_cross_dimensions(SumMetric("revenue"), "channel", "device")
    # base_df rows: (a, mobile) and (b, desktop) across both periods — 2 unique combos
    assert cross["total_cells"] == 2


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


# ── Shapley attribution tests ─────────────────────────────────────────────────

def test_shapley_attributed_sum_equals_total_effect():
    """mix_attributed + rate_attributed == total_effect for every segment."""
    lens = MetricLens(base_df(), "date", ("2026-01-01", "2026-01-01"), ("2026-01-02", "2026-01-02"), ["channel"])
    result = lens.analyze(RatioMetric("orders", "sessions", name="cvr"))
    rows = result.to_dict()["dimensions"][0]["segment_contributions"]
    for row in rows:
        assert row["mix_attributed"] + row["rate_attributed"] == pytest.approx(row["total_effect"])


def test_shapley_splits_cross_term_equally():
    """mix_attributed = mix_effect + cross/2 and rate_attributed = rate_effect + cross/2."""
    lens = MetricLens(base_df(), "date", ("2026-01-01", "2026-01-01"), ("2026-01-02", "2026-01-02"), ["channel"])
    result = lens.analyze(RatioMetric("orders", "sessions", name="cvr"))
    rows = result.to_dict()["dimensions"][0]["segment_contributions"]
    for row in rows:
        assert row["mix_attributed"] == pytest.approx(row["mix_effect"] + row["cross_term"] / 2)
        assert row["rate_attributed"] == pytest.approx(row["rate_effect"] + row["cross_term"] / 2)


# ── Bootstrap CI tests ────────────────────────────────────────────────────────

def _multi_date_df():
    """5-date dataset with 2 channels — enough dates for meaningful bootstrap resampling."""
    rows = []
    for day in range(1, 6):
        rows.append({"date": f"2026-01-{day:02d}", "channel": "a", "orders": 10 + day, "sessions": 100})
        rows.append({"date": f"2026-01-{day:02d}", "channel": "b", "orders": 5 + day, "sessions": 80})
    for day in range(6, 11):
        rows.append({"date": f"2026-01-{day:02d}", "channel": "a", "orders": 8 + day, "sessions": 100})
        rows.append({"date": f"2026-01-{day:02d}", "channel": "b", "orders": 6 + day, "sessions": 80})
    return pd.DataFrame(rows)


def test_bootstrap_ci_keys_present():
    """bootstrap_cis payload contains expected top-level keys."""
    lens = MetricLens(_multi_date_df(), "date", ("2026-01-01", "2026-01-05"), ("2026-01-06", "2026-01-10"), ["channel"])
    result = lens.analyze(RatioMetric("orders", "sessions", name="cvr"), bootstrap_n=50)
    cis = result.to_dict()["bootstrap_cis"]
    assert cis is not None
    assert cis["n_bootstrap"] == 50
    assert "dimensions" in cis
    assert "channel" in cis["dimensions"]


def test_bootstrap_ci_bounds_are_finite():
    """lo and hi bounds for total_effect are finite floats for all segments."""
    lens = MetricLens(_multi_date_df(), "date", ("2026-01-01", "2026-01-05"), ("2026-01-06", "2026-01-10"), ["channel"])
    result = lens.analyze(RatioMetric("orders", "sessions", name="cvr"), bootstrap_n=50)
    cis = result.to_dict()["bootstrap_cis"]["dimensions"]["channel"]
    for seg_data in cis.values():
        assert "total_effect" in seg_data
        lo = seg_data["total_effect"]["lo"]
        hi = seg_data["total_effect"]["hi"]
        assert lo <= hi
        assert lo == lo and hi == hi  # not NaN


def test_bootstrap_ci_none_when_bootstrap_n_is_zero():
    """bootstrap_cis is None when bootstrap_n=0 (default)."""
    lens = MetricLens(base_df(), "date", ("2026-01-01", "2026-01-01"), ("2026-01-02", "2026-01-02"), ["channel"])
    result = lens.analyze(RatioMetric("orders", "sessions", name="cvr"))
    assert result.to_dict()["bootstrap_cis"] is None
