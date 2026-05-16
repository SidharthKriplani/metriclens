from __future__ import annotations

from dataclasses import asdict
from typing import Any

import numpy as np
import pandas as pd

from metriclens._version import __version__
from metriclens.decomposition import (
    FLAT_EPSILON,
    additive_decomposition,
    normalize_dimension_nulls,
    ratio_decomposition,
)
from metriclens.metrics import MetricSpec
from metriclens.profiler import DataProfiler
from metriclens.report import AnalysisResult, MANDATORY_INTERPRETATION_NOTE


class MetricLens:
    """Analyze metric movement between two inclusive date periods."""

    def __init__(
        self,
        data: pd.DataFrame,
        date_col: str,
        baseline_period: tuple[str, str],
        current_period: tuple[str, str],
        dimensions: list[str],
    ):
        self.data = data.copy(deep=True)
        self.date_col = date_col
        self.baseline_period = _parse_period(baseline_period)
        self.current_period = _parse_period(current_period)
        self.dimensions = dimensions
        self._validate_columns()
        self.data[self.date_col] = pd.to_datetime(self.data[self.date_col]).dt.normalize()

    def analyze(self, metric: MetricSpec, *, bootstrap_n: int = 0, bootstrap_seed: int = 42) -> AnalysisResult:
        working = normalize_dimension_nulls(self.data, self.dimensions)
        baseline_df = self._slice_period(working, self.baseline_period)
        current_df = self._slice_period(working, self.current_period)

        baseline_value = metric.compute(baseline_df)
        current_value = metric.compute(current_df)
        total_delta = current_value - baseline_value
        relative_delta_pct = None if baseline_value == 0 else (total_delta / baseline_value) * 100
        direction = "FLAT" if abs(total_delta) < FLAT_EPSILON else ("UP" if total_delta > 0 else "DOWN")

        quality_checks = DataProfiler(self.date_col, self.dimensions).profile(
            working, baseline_df, current_df, self.baseline_period, self.current_period
        )

        dimensions_payload: list[dict[str, Any]] = []
        identity_residuals = []
        for dimension in self.dimensions:
            if metric.decomposition_type == "additive":
                rows = additive_decomposition(
                    metric,
                    baseline_df,
                    current_df,
                    dimension,
                    baseline_value,
                    current_value,
                )
                residual = None
            else:
                rows = ratio_decomposition(
                    metric,
                    baseline_df,
                    current_df,
                    dimension,
                    baseline_value,
                    current_value,
                )
                residual = total_delta - sum(float(row["total_effect"]) for row in rows)
            if residual is not None:
                identity_residuals.append({"dimension": dimension, "identity_residual": residual})
            dimensions_payload.append(
                {
                    "dimension": dimension,
                    "segment_contributions": rows,
                    "top_segments": rows[:5],
                    "identity_residual": residual,
                }
            )

        # Cross-dimension interaction: auto-computed when ≥2 dimensions are present
        cross_dimension_interactions: dict[str, Any] | None = None
        if len(self.dimensions) >= 2:
            try:
                cross_dimension_interactions = self.analyze_cross_dimensions(
                    metric, self.dimensions[0], self.dimensions[1]
                )
            except Exception:
                cross_dimension_interactions = None

        # Bootstrap confidence intervals (optional)
        bootstrap_cis: dict[str, Any] | None = None
        if bootstrap_n > 0 and metric.decomposition_type == "ratio":
            bootstrap_cis = _bootstrap_ratio_cis(
                metric=metric,
                working=working,
                date_col=self.date_col,
                baseline_period=self.baseline_period,
                current_period=self.current_period,
                dimensions=self.dimensions,
                n_bootstrap=bootstrap_n,
                seed=bootstrap_seed,
            )

        payload = {
            "schema_version": "1.0",
            "metadata": {
                "metric_name": metric.display_name,
                "metric_type": metric.__class__.__name__,
                "display_unit": metric.display_unit,
                "decomposition_type": metric.decomposition_type,
                "package_version": __version__,
                "date_col": self.date_col,
                "baseline_period": [str(self.baseline_period[0].date()), str(self.baseline_period[1].date())],
                "current_period": [str(self.current_period[0].date()), str(self.current_period[1].date())],
                "dimensions": self.dimensions,
            },
            "executive_summary": {
                "baseline_value": baseline_value,
                "current_value": current_value,
                "absolute_delta": total_delta,
                "relative_delta_pct": relative_delta_pct,
                "direction": direction,
            },
            "quality_checks": [asdict(check) for check in quality_checks],
            "dimensions": dimensions_payload,
            "identity_checks": identity_residuals,
            "cross_dimension_interactions": cross_dimension_interactions,
            "investigation_areas": _investigation_areas(dimensions_payload, metric.decomposition_type),
            "bootstrap_cis": bootstrap_cis,
            "interpretation_note": MANDATORY_INTERPRETATION_NOTE,
        }
        return AnalysisResult(payload)

    def analyze_cross_dimensions(
        self,
        metric: MetricSpec,
        dim1: str,
        dim2: str,
    ) -> dict[str, Any]:
        """Decompose metric delta across the Cartesian product of two dimensions.

        Creates a synthetic cross-product column ('dim1 / dim2') and runs the
        standard additive or ratio decomposition on it, revealing which specific
        (channel, device) or similar cell pairs drove the headline metric move.
        """
        if dim1 not in self.data.columns or dim2 not in self.data.columns:
            raise ValueError(
                f"Both dimensions '{dim1}' and '{dim2}' must be present in the data."
            )
        cross_col = f"{dim1} / {dim2}"
        working = normalize_dimension_nulls(self.data, [dim1, dim2]).copy()
        working[cross_col] = working[dim1].astype(str) + " / " + working[dim2].astype(str)

        baseline_df = self._slice_period(working, self.baseline_period)
        current_df = self._slice_period(working, self.current_period)
        baseline_total = metric.compute(baseline_df)
        current_total = metric.compute(current_df)

        if metric.decomposition_type == "additive":
            rows = additive_decomposition(
                metric, baseline_df, current_df, cross_col, baseline_total, current_total
            )
        else:
            rows = ratio_decomposition(
                metric, baseline_df, current_df, cross_col, baseline_total, current_total
            )

        # Annotate each row with the split dimension values for readability
        for row in rows:
            parts = str(row.get("segment", "")).split(" / ", 1)
            row[dim1] = parts[0] if parts else None
            row[dim2] = parts[1] if len(parts) == 2 else None

        return {
            "dim1": dim1,
            "dim2": dim2,
            "cross_label": cross_col,
            "total_cells": len(rows),
            "top_interactions": rows[:10],
            "all_interactions": rows,
        }

    def _slice_period(
        self, data: pd.DataFrame, period: tuple[pd.Timestamp, pd.Timestamp]
    ) -> pd.DataFrame:
        start, end = period
        return data[(data[self.date_col] >= start) & (data[self.date_col] <= end)].copy()

    def _validate_columns(self) -> None:
        missing = [col for col in [self.date_col, *self.dimensions] if col not in self.data.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")


def _parse_period(period: tuple[str, str]) -> tuple[pd.Timestamp, pd.Timestamp]:
    start, end = pd.to_datetime(period[0]).normalize(), pd.to_datetime(period[1]).normalize()
    if start > end:
        raise ValueError("Period start must be on or before period end.")
    return start, end


def _bootstrap_ratio_cis(
    metric: MetricSpec,
    working: pd.DataFrame,
    date_col: str,
    baseline_period: tuple[pd.Timestamp, pd.Timestamp],
    current_period: tuple[pd.Timestamp, pd.Timestamp],
    dimensions: list[str],
    n_bootstrap: int,
    seed: int,
    ci_level: float = 0.95,
) -> dict[str, Any]:
    """Bootstrap date-resampled confidence intervals on segment decomposition effects.

    Resamples baseline and current dates independently with replacement n_bootstrap times.
    For each bootstrap sample, recomputes the ratio decomposition and collects per-segment
    mix_effect, rate_effect, cross_term, mix_attributed, rate_attributed, total_effect.
    Returns (1-ci_level)/2 and (1+ci_level)/2 percentile bounds per segment per dimension.
    """
    rng = np.random.default_rng(seed)
    alpha = (1.0 - ci_level) / 2

    baseline_df_full = working[(working[date_col] >= baseline_period[0]) & (working[date_col] <= baseline_period[1])].copy()
    current_df_full = working[(working[date_col] >= current_period[0]) & (working[date_col] <= current_period[1])].copy()

    baseline_dates = baseline_df_full[date_col].unique()
    current_dates = current_df_full[date_col].unique()

    ci_fields = ["mix_effect", "rate_effect", "cross_term", "mix_attributed", "rate_attributed", "total_effect"]
    # Accumulate bootstrap draws: {dimension: {segment: {field: [values]}}}
    accumulators: dict[str, dict[str, dict[str, list[float]]]] = {dim: {} for dim in dimensions}

    for _ in range(n_bootstrap):
        b_dates = rng.choice(baseline_dates, size=len(baseline_dates), replace=True)
        c_dates = rng.choice(current_dates, size=len(current_dates), replace=True)
        b_sample = baseline_df_full[baseline_df_full[date_col].isin(b_dates)]
        c_sample = current_df_full[current_df_full[date_col].isin(c_dates)]
        b_val = metric.compute(b_sample)
        c_val = metric.compute(c_sample)
        for dim in dimensions:
            rows = ratio_decomposition(metric, b_sample, c_sample, dim, b_val, c_val)
            for row in rows:
                seg = str(row["segment"])
                if seg not in accumulators[dim]:
                    accumulators[dim][seg] = {f: [] for f in ci_fields}
                for f in ci_fields:
                    val = row.get(f)
                    if val is not None:
                        accumulators[dim][seg][f].append(float(val))

    # Build CI output
    result: dict[str, Any] = {
        "n_bootstrap": n_bootstrap,
        "ci_level": ci_level,
        "method": "date_resample",
        "dimensions": {},
    }
    for dim, segments in accumulators.items():
        result["dimensions"][dim] = {}
        for seg, fields in segments.items():
            result["dimensions"][dim][seg] = {}
            for f, vals in fields.items():
                if len(vals) >= 2:
                    arr = np.array(vals)
                    result["dimensions"][dim][seg][f] = {
                        "mean": float(np.mean(arr)),
                        "lo": float(np.quantile(arr, alpha)),
                        "hi": float(np.quantile(arr, 1 - alpha)),
                    }
    return result


def _investigation_areas(dimensions_payload: list[dict[str, Any]], decomposition_type: str) -> list[str]:
    candidates = []
    for dimension in dimensions_payload:
        rows = dimension["segment_contributions"]
        if not rows:
            continue
        key = "total_effect" if decomposition_type == "ratio" else "segment_delta"
        top = max(rows, key=lambda row: abs(float(row.get(key) or 0.0)))
        value = top.get(key)
        candidates.append(
            f"Investigate {dimension['dimension']}={top['segment']} first; it has the largest absolute {key} signal ({value})."
        )
    return candidates[:5]
