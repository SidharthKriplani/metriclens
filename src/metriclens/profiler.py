from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd


@dataclass(frozen=True)
class QualityCheckResult:
    check: str
    status: str
    detail: str
    value: float | int | str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


class DataProfiler:
    """Small profiler for v0 MetricLens input quality checks."""

    def __init__(self, date_col: str, dimensions: list[str]):
        self.date_col = date_col
        self.dimensions = dimensions

    def profile(
        self,
        df: pd.DataFrame,
        baseline_df: pd.DataFrame,
        current_df: pd.DataFrame,
        baseline_period: tuple[pd.Timestamp, pd.Timestamp],
        current_period: tuple[pd.Timestamp, pd.Timestamp],
    ) -> list[QualityCheckResult]:
        checks: list[QualityCheckResult] = []
        checks.extend(self._row_count_checks(baseline_df, current_df))
        checks.extend(self._date_coverage_checks(baseline_df, baseline_period, "baseline"))
        checks.extend(self._date_coverage_checks(current_df, current_period, "current"))
        checks.extend(self._period_length_check(baseline_period, current_period))
        checks.extend(self._null_rate_checks(df))
        checks.extend(self._grain_checks(df))
        return checks

    def _row_count_checks(self, baseline_df: pd.DataFrame, current_df: pd.DataFrame) -> list[QualityCheckResult]:
        out = []
        for label, part in [("baseline", baseline_df), ("current", current_df)]:
            status = "PASS" if len(part) > 0 else "FAIL"
            out.append(
                QualityCheckResult(
                    check=f"row_count_{label}",
                    status=status,
                    detail=f"{label} period contains {len(part)} rows.",
                    value=len(part),
                )
            )
        return out

    def _date_coverage_checks(
        self, part: pd.DataFrame, period: tuple[pd.Timestamp, pd.Timestamp], label: str
    ) -> list[QualityCheckResult]:
        if part.empty:
            return [
                QualityCheckResult(
                    check=f"date_coverage_{label}",
                    status="FAIL",
                    detail=f"{label} period has no rows, so date coverage cannot be established.",
                    value=None,
                )
            ]
        expected = pd.date_range(period[0], period[1], freq="D")
        observed = pd.to_datetime(part[self.date_col]).dt.normalize().drop_duplicates()
        observed_set = set(observed)
        missing = [d for d in expected if d not in observed_set]
        missing_ratio = len(missing) / max(len(expected), 1)
        if missing_ratio == 0:
            status = "PASS"
        elif missing_ratio > 0.20:
            status = "FAIL"
        else:
            status = "WARN"
        return [
            QualityCheckResult(
                check=f"date_coverage_{label}",
                status=status,
                detail=f"{label} period missing {len(missing)} of {len(expected)} expected dates.",
                value=round(missing_ratio, 6),
            )
        ]

    def _period_length_check(
        self, baseline_period: tuple[pd.Timestamp, pd.Timestamp], current_period: tuple[pd.Timestamp, pd.Timestamp]
    ) -> list[QualityCheckResult]:
        baseline_days = (baseline_period[1] - baseline_period[0]).days + 1
        current_days = (current_period[1] - current_period[0]).days + 1
        status = "PASS" if baseline_days == current_days else "WARN"
        return [
            QualityCheckResult(
                check="period_length_match",
                status=status,
                detail=f"baseline has {baseline_days} days; current has {current_days} days.",
                value=f"{baseline_days}:{current_days}",
            )
        ]

    def _null_rate_checks(self, df: pd.DataFrame) -> list[QualityCheckResult]:
        out = []
        for dimension in self.dimensions:
            rate = float(df[dimension].isna().mean()) if len(df) else 0.0
            if rate >= 0.15:
                status = "FAIL"
            elif rate >= 0.03:
                status = "WARN"
            else:
                status = "PASS"
            out.append(
                QualityCheckResult(
                    check=f"null_rate_{dimension}",
                    status=status,
                    detail=f"{dimension} null rate is {rate:.2%}. Nulls are analyzed as '(null)' in the working copy.",
                    value=round(rate, 6),
                )
            )
        return out

    def _grain_checks(self, df: pd.DataFrame) -> list[QualityCheckResult]:
        grain_cols = [self.date_col, *self.dimensions]
        duplicate_count = int(df.duplicated(subset=grain_cols).sum()) if len(df) else 0
        status = "PASS" if duplicate_count == 0 else "WARN"
        return [
            QualityCheckResult(
                check="duplicate_grain",
                status=status,
                detail=(
                    f"Found {duplicate_count} duplicate rows at grain "
                    f"{self.date_col} x {' x '.join(self.dimensions)}."
                ),
                value=duplicate_count,
            )
        ]
