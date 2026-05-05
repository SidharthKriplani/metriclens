from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np
import pandas as pd

from metriclens.exceptions import ZeroDenominatorError


class MetricSpec(ABC):
    """Abstract metric contract used by the decomposition engine."""

    @abstractmethod
    def compute(self, df: pd.DataFrame) -> float:
        """Aggregate a DataFrame to a scalar metric value."""

    @abstractmethod
    def compute_by_group(self, df: pd.DataFrame, dimension: str) -> pd.DataFrame:
        """Return segment-level values needed for decomposition."""

    @property
    @abstractmethod
    def decomposition_type(self) -> str:
        """Return either 'additive' or 'ratio'."""

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name used in reports."""

    @property
    def display_unit(self) -> str:
        return "value"


@dataclass(frozen=True)
class SumMetric(MetricSpec):
    column: str
    name: str | None = None

    def compute(self, df: pd.DataFrame) -> float:
        return float(df[self.column].sum())

    def compute_by_group(self, df: pd.DataFrame, dimension: str) -> pd.DataFrame:
        out = df.groupby(dimension, dropna=False, as_index=False)[self.column].sum()
        return out.rename(columns={self.column: "value", dimension: "segment"})

    @property
    def decomposition_type(self) -> str:
        return "additive"

    @property
    def display_name(self) -> str:
        return self.name or self.column


@dataclass(frozen=True)
class CountMetric(MetricSpec):
    column: str | None = None
    name: str | None = None

    def compute(self, df: pd.DataFrame) -> float:
        if self.column is None:
            return float(len(df))
        return float(df[self.column].notna().sum())

    def compute_by_group(self, df: pd.DataFrame, dimension: str) -> pd.DataFrame:
        if self.column is None:
            out = df.groupby(dimension, dropna=False).size().reset_index(name="value")
        else:
            out = df.groupby(dimension, dropna=False)[self.column].count().reset_index(name="value")
        return out.rename(columns={dimension: "segment"})

    @property
    def decomposition_type(self) -> str:
        return "additive"

    @property
    def display_name(self) -> str:
        return self.name or (f"count_{self.column}" if self.column else "row_count")


@dataclass(frozen=True)
class RatioMetric(MetricSpec):
    numerator: str
    denominator: str
    name: str | None = None

    def compute(self, df: pd.DataFrame) -> float:
        numerator = float(df[self.numerator].sum())
        denominator = float(df[self.denominator].sum())
        if denominator == 0:
            raise ZeroDenominatorError(
                f"Cannot compute ratio metric '{self.display_name}' because denominator is zero."
            )
        return numerator / denominator

    def compute_by_group(self, df: pd.DataFrame, dimension: str) -> pd.DataFrame:
        out = (
            df.groupby(dimension, dropna=False, as_index=False)[[self.numerator, self.denominator]]
            .sum()
            .rename(
                columns={
                    dimension: "segment",
                    self.numerator: "numerator",
                    self.denominator: "denominator",
                }
            )
        )
        out["rate"] = np.where(out["denominator"] != 0, out["numerator"] / out["denominator"], 0.0)
        return out

    @property
    def decomposition_type(self) -> str:
        return "ratio"

    @property
    def display_name(self) -> str:
        return self.name or f"{self.numerator}_per_{self.denominator}"

    @property
    def display_unit(self) -> str:
        return "rate"


@dataclass(frozen=True)
class AverageMetric(MetricSpec):
    value: str
    weight: str | None = None
    name: str | None = None

    def compute(self, df: pd.DataFrame) -> float:
        if self.weight is None:
            denominator = len(df)
            if denominator == 0:
                raise ZeroDenominatorError(
                    f"Cannot compute average metric '{self.display_name}' because row count is zero."
                )
            return float(df[self.value].sum()) / denominator
        denominator = float(df[self.weight].sum())
        if denominator == 0:
            raise ZeroDenominatorError(
                f"Cannot compute weighted average metric '{self.display_name}' because weight sum is zero."
            )
        return float((df[self.value] * df[self.weight]).sum()) / denominator

    def compute_by_group(self, df: pd.DataFrame, dimension: str) -> pd.DataFrame:
        working = df.copy()
        if self.weight is None:
            working["__metriclens_numerator"] = working[self.value]
            working["__metriclens_denominator"] = 1.0
        else:
            working["__metriclens_numerator"] = working[self.value] * working[self.weight]
            working["__metriclens_denominator"] = working[self.weight]
        out = (
            working.groupby(dimension, dropna=False, as_index=False)[
                ["__metriclens_numerator", "__metriclens_denominator"]
            ]
            .sum()
            .rename(
                columns={
                    dimension: "segment",
                    "__metriclens_numerator": "numerator",
                    "__metriclens_denominator": "denominator",
                }
            )
        )
        out["rate"] = np.where(out["denominator"] != 0, out["numerator"] / out["denominator"], 0.0)
        return out

    @property
    def decomposition_type(self) -> str:
        return "ratio"

    @property
    def display_name(self) -> str:
        return self.name or f"avg_{self.value}"

    @property
    def display_unit(self) -> str:
        return "average"
