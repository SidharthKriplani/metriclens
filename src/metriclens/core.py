from __future__ import annotations

from dataclasses import asdict
from typing import Any

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

    def analyze(self, metric: MetricSpec) -> AnalysisResult:
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

        payload = {
            "schema_version": "0.1",
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
            "investigation_areas": _investigation_areas(dimensions_payload, metric.decomposition_type),
            "interpretation_note": MANDATORY_INTERPRETATION_NOTE,
        }
        return AnalysisResult(payload)

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
