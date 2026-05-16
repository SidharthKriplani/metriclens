# MetricLens Report: revenue

## 1. Executive Summary
- Baseline value: `21830228.73`
- Current value: `20592614.64`
- Absolute delta: `-1237614.0899999999`
- Relative delta pct: `-5.669267625671826`
- Direction: `DOWN`

## 2. Data Quality Summary
- **PASS** `row_count_baseline` — baseline period contains 378 rows.
- **PASS** `row_count_current` — current period contains 378 rows.
- **PASS** `date_coverage_baseline` — baseline period missing 0 of 7 expected dates.
- **PASS** `date_coverage_current` — current period missing 0 of 7 expected dates.
- **PASS** `period_length_match` — baseline has 7 days; current has 7 days.
- **PASS** `null_rate_channel` — channel null rate is 0.00%. Nulls are analyzed as '(null)' in the working copy.
- **PASS** `null_rate_device` — device null rate is 0.00%. Nulls are analyzed as '(null)' in the working copy.
- **PASS** `null_rate_city` — city null rate is 0.00%. Nulls are analyzed as '(null)' in the working copy.
- **PASS** `null_rate_category` — category null rate is 0.00%. Nulls are analyzed as '(null)' in the working copy.
- **PASS** `duplicate_grain` — Found 0 duplicate rows at grain date x channel x device x city x category.

## 3. Segment Contributions

### Dimension: channel
| segment | segment_status | baseline_value | current_value | segment_delta | contribution_pct |
| --- | --- | --- | --- | --- | --- |
| paid_search | existing | 1.06738e+07 | 1.00426e+07 | -631232 | 51.004 |
| organic | existing | 7.66449e+06 | 7.10694e+06 | -557548 | 45.0502 |
| email | existing | 3.49195e+06 | 3.44312e+06 | -48834 | 3.94582 |

### Dimension: device
| segment | segment_status | baseline_value | current_value | segment_delta | contribution_pct |
| --- | --- | --- | --- | --- | --- |
| mobile | existing | 1.31145e+07 | 1.23973e+07 | -717241 | 57.9535 |
| desktop | existing | 8.71574e+06 | 8.19536e+06 | -520373 | 42.0465 |

### Dimension: city
| segment | segment_status | baseline_value | current_value | segment_delta | contribution_pct |
| --- | --- | --- | --- | --- | --- |
| Bengaluru | existing | 8.74349e+06 | 8.01985e+06 | -723637 | 58.4704 |
| Delhi | existing | 6.18642e+06 | 5.73739e+06 | -449029 | 36.2818 |
| Mumbai | existing | 6.90032e+06 | 6.83537e+06 | -64948 | 5.24784 |

### Dimension: category
| segment | segment_status | baseline_value | current_value | segment_delta | contribution_pct |
| --- | --- | --- | --- | --- | --- |
| skincare | existing | 1.00864e+07 | 9.37563e+06 | -710761 | 57.43 |
| baby | existing | 7.56875e+06 | 7.21737e+06 | -351382 | 28.3919 |
| fitness | existing | 4.17509e+06 | 3.99962e+06 | -175471 | 14.1782 |

## 4. Mix / Rate / Cross Decomposition
Not applicable for additive metrics.

## 5. Investigation Areas
- Investigate channel=paid_search first; it has the largest absolute segment_delta signal (-631232.0999999996).
- Investigate device=mobile first; it has the largest absolute segment_delta signal (-717240.959999999).
- Investigate city=Bengaluru first; it has the largest absolute segment_delta signal (-723637.330000001).
- Investigate category=skincare first; it has the largest absolute segment_delta signal (-710761.2600000016).

## 6. Interpretation Note
MetricLens reports deterministic metric movement decomposition. It identifies segment contributors, mix effects, rate effects, and cross terms. It does not claim causality, statistical significance, anomaly detection, or root cause proof. Use these outputs as investigation signals, not automatic decisions.

## 7. Schema
schema_version: `1.0`
