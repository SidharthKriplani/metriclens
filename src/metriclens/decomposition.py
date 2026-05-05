from __future__ import annotations

import numpy as np
import pandas as pd

from metriclens.metrics import MetricSpec

FLAT_EPSILON = 1e-9
NULL_SEGMENT = "(null)"


def normalize_dimension_nulls(df: pd.DataFrame, dimensions: list[str]) -> pd.DataFrame:
    working = df.copy(deep=True)
    for dimension in dimensions:
        working[dimension] = working[dimension].where(working[dimension].notna(), NULL_SEGMENT)
    return working


def additive_decomposition(
    metric: MetricSpec,
    baseline_df: pd.DataFrame,
    current_df: pd.DataFrame,
    dimension: str,
    baseline_total: float,
    current_total: float,
) -> list[dict]:
    baseline = metric.compute_by_group(baseline_df, dimension).rename(columns={"value": "baseline_value"})
    current = metric.compute_by_group(current_df, dimension).rename(columns={"value": "current_value"})
    merged = baseline.merge(current, on="segment", how="outer").fillna(0.0)
    merged["segment_delta"] = merged["current_value"] - merged["baseline_value"]
    total_delta = current_total - baseline_total
    merged["contribution_pct"] = np.where(
        abs(total_delta) < FLAT_EPSILON,
        None,
        merged["segment_delta"] / total_delta * 100,
    )
    merged["baseline_share"] = np.where(
        baseline_total != 0, merged["baseline_value"] / baseline_total, None
    )
    merged["current_share"] = np.where(current_total != 0, merged["current_value"] / current_total, None)
    merged["share_delta"] = merged["current_share"] - merged["baseline_share"]
    merged["segment_status"] = np.select(
        [
            (merged["baseline_value"] == 0) & (merged["current_value"] != 0),
            (merged["baseline_value"] != 0) & (merged["current_value"] == 0),
        ],
        ["new", "disappeared"],
        default="existing",
    )
    merged["dimension"] = dimension
    merged = merged.sort_values("segment_delta", key=lambda s: s.abs(), ascending=False)
    cols = [
        "dimension",
        "segment",
        "segment_status",
        "baseline_value",
        "current_value",
        "segment_delta",
        "contribution_pct",
        "baseline_share",
        "current_share",
        "share_delta",
    ]
    return _records(merged[cols])


def ratio_decomposition(
    metric: MetricSpec,
    baseline_df: pd.DataFrame,
    current_df: pd.DataFrame,
    dimension: str,
    baseline_value: float,
    current_value: float,
) -> list[dict]:
    baseline = metric.compute_by_group(baseline_df, dimension).rename(
        columns={
            "numerator": "baseline_numerator",
            "denominator": "baseline_denominator",
            "rate": "baseline_rate",
        }
    )
    current = metric.compute_by_group(current_df, dimension).rename(
        columns={
            "numerator": "current_numerator",
            "denominator": "current_denominator",
            "rate": "current_rate",
        }
    )
    merged = baseline.merge(current, on="segment", how="outer").fillna(0.0)

    baseline_denominator_total = float(merged["baseline_denominator"].sum())
    current_denominator_total = float(merged["current_denominator"].sum())

    merged["baseline_weight"] = np.where(
        baseline_denominator_total != 0,
        merged["baseline_denominator"] / baseline_denominator_total,
        0.0,
    )
    merged["current_weight"] = np.where(
        current_denominator_total != 0,
        merged["current_denominator"] / current_denominator_total,
        0.0,
    )
    merged["rate_delta"] = merged["current_rate"] - merged["baseline_rate"]
    merged["weight_delta"] = merged["current_weight"] - merged["baseline_weight"]
    merged["mix_effect"] = merged["weight_delta"] * merged["baseline_rate"]
    merged["rate_effect"] = merged["baseline_weight"] * merged["rate_delta"]
    merged["cross_term"] = merged["weight_delta"] * merged["rate_delta"]
    merged["total_effect"] = merged["mix_effect"] + merged["rate_effect"] + merged["cross_term"]

    total_delta = current_value - baseline_value
    merged["contribution_pct"] = np.where(
        abs(total_delta) < FLAT_EPSILON,
        None,
        merged["total_effect"] / total_delta * 100,
    )
    merged["segment_status"] = np.select(
        [
            (merged["baseline_denominator"] == 0) & (merged["current_denominator"] != 0),
            (merged["baseline_denominator"] != 0) & (merged["current_denominator"] == 0),
        ],
        ["new", "disappeared"],
        default="existing",
    )
    merged["dimension"] = dimension
    merged = merged.sort_values("total_effect", key=lambda s: s.abs(), ascending=False)
    cols = [
        "dimension",
        "segment",
        "segment_status",
        "baseline_numerator",
        "baseline_denominator",
        "baseline_rate",
        "baseline_weight",
        "current_numerator",
        "current_denominator",
        "current_rate",
        "current_weight",
        "weight_delta",
        "rate_delta",
        "mix_effect",
        "rate_effect",
        "cross_term",
        "total_effect",
        "contribution_pct",
    ]
    return _records(merged[cols])


def _records(df: pd.DataFrame) -> list[dict]:
    clean = df.replace({np.nan: None})
    return clean.to_dict(orient="records")
