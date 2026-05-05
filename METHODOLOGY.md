# MetricLens Methodology

## What MetricLens does

MetricLens decomposes metric movement between a baseline period and a current period. It identifies segment contributors and, for ratio or average metrics, separates movement into mix effect, rate effect, and cross term.

## What it does not do

MetricLens does not infer causality, run experiments, perform anomaly detection, compute statistical significance, forecast future values, or decide what action to take.

## Metric types and decomposition

MetricLens v0.1.0 supports four metric types:

- `SumMetric`: additive metric such as revenue.
- `CountMetric`: additive count of rows or non-null values.
- `RatioMetric`: numerator divided by denominator, such as orders / sessions.
- `AverageMetric`: treated as a ratio of value-sum to count or weighted-sum to weight-sum.

## Additive decomposition

For additive metrics, each segment contribution is:

```text
segment_delta_s = current_value_s - baseline_value_s
```

The total metric delta is:

```text
total_delta = current_total - baseline_total
```

Contribution percentage is:

```text
contribution_pct_s = segment_delta_s / total_delta
```

When `abs(total_delta) < 1e-9`, contribution percentage is `None` for all segments because there is no meaningful signed total to divide by.

When `baseline_value == 0`, relative delta percentage is `None` because percentage growth from zero is undefined.

## Ratio decomposition — full algebraic derivation

For a ratio metric, let each segment `s` have:

```text
w_b_s = baseline denominator share for segment s
w_c_s = current denominator share for segment s
r_b_s = baseline rate for segment s
r_c_s = current rate for segment s
```

The population-level baseline and current rates are:

```text
R_b = Σ_s w_b_s * r_b_s
R_c = Σ_s w_c_s * r_c_s
```

The segment-level movement is:

```text
w_c_s * r_c_s - w_b_s * r_b_s
```

Add and subtract terms to decompose it:

```text
w_c_s*r_c_s - w_b_s*r_b_s
= (w_c_s - w_b_s)*r_b_s
  + w_b_s*(r_c_s - r_b_s)
  + (w_c_s - w_b_s)*(r_c_s - r_b_s)
```

MetricLens names these:

```text
mix_effect_s   = (w_c_s - w_b_s) * r_b_s
rate_effect_s  = w_b_s * (r_c_s - r_b_s)
cross_term_s   = (w_c_s - w_b_s) * (r_c_s - r_b_s)
total_effect_s = mix_effect_s + rate_effect_s + cross_term_s
```

Summing `total_effect_s` across all segments equals `R_c - R_b`, up to floating-point precision.

## Cross-term semantics

The cross term is the interaction between weight movement and rate movement. MetricLens reports it explicitly because discarding it hides part of the exact identity.

## New and disappeared segments — corrected formulas

MetricLens uses zero-fill convention for segments that appear in only one period.

For a new segment:

```text
w_b = 0
r_b = 0
w_c > 0
r_c >= 0
```

For a disappeared segment:

```text
w_c = 0
r_c = 0
w_b > 0
r_b >= 0
```

The disappeared segment cross-term is therefore:

```text
cross_term = (0 - w_b) * (0 - r_b) = +w_b * r_b
```

It is positive, not zero. This is required for the ratio identity to hold under zero-fill convention.

## Null dimension handling

MetricLens never modifies the original DataFrame. It creates an internal working copy and replaces null dimension values with `"(null)"` so missing segment labels remain visible in the output.

## AverageMetric as ratio

An average can be represented as:

```text
average = numerator / denominator
```

For unweighted averages, numerator is the sum of values and denominator is row count. For weighted averages, numerator is `sum(value * weight)` and denominator is `sum(weight)`. This makes `AverageMetric` compatible with the same mix/rate/cross decomposition used by `RatioMetric`.

## Contribution vs causation

A segment contribution is an accounting identity, not a causal claim. If paid-search mobile accounts for most of a conversion-rate drop, that means the segment is a strong investigation area. It does not prove paid-search mobile caused the drop.

## Limitations

- v0 analyzes one dimension at a time.
- v0 is retrospective only.
- v0 does not compute confidence intervals or p-values.
- v0 does not support CLI, dashboarding, Shapley attribution, or opportunity ranking.
- v0 output is only JSON, Markdown, and HTML.

## Version history

- v0.1.0: Movement Mode only: metric classes, additive decomposition, ratio mix/rate/cross decomposition, data profiler, reports, tests, synthetic e-commerce demo.
