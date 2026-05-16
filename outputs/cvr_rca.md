# MetricLens Report: cvr

## 1. Executive Summary
- Baseline value: `0.07168976989773702`
- Current value: `0.06352213171686556`
- Absolute delta: `-0.008167638180871462`
- Relative delta pct: `-11.393031659220437`
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
| segment | segment_status | baseline_rate | current_rate | mix_effect | rate_effect | cross_term | total_effect | mix_attributed | rate_attributed | contribution_pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| paid_search | existing | 0.0730122 | 0.057987 | 0.00374848 | -0.00724257 | -0.000771402 | -0.00426549 | 0.00336278 | -0.00762827 | 52.2242 |
| organic | existing | 0.0676853 | 0.066806 | -0.00275829 | -0.000324791 | 3.58327e-05 | -0.00304725 | -0.00274037 | -0.000306874 | 37.3088 |
| email | existing | 0.0773542 | 0.0770947 | -0.000819084 | -3.85672e-05 | 2.74824e-06 | -0.000854903 | -0.00081771 | -3.71931e-05 | 10.467 |

### Dimension: device
| segment | segment_status | baseline_rate | current_rate | mix_effect | rate_effect | cross_term | total_effect | mix_attributed | rate_attributed | contribution_pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mobile | existing | 0.0707175 | 0.0581937 | 0.00301446 | -0.00767385 | -0.000533847 | -0.00519323 | 0.00274754 | -0.00794077 | 63.583 |
| desktop | existing | 0.0732282 | 0.073655 | -0.00312149 | 0.000165279 | -1.8193e-05 | -0.00297441 | -0.00313059 | 0.000156183 | 36.417 |

### Dimension: city
| segment | segment_status | baseline_rate | current_rate | mix_effect | rate_effect | cross_term | total_effect | mix_attributed | rate_attributed | contribution_pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Bengaluru | existing | 0.0756096 | 0.0660837 | -0.000321055 | -0.00360847 | 4.04493e-05 | -0.00388908 | -0.00030083 | -0.00358825 | 47.6157 |
| Delhi | existing | 0.0686535 | 0.0598767 | -9.18793e-05 | -0.00261201 | 1.17461e-05 | -0.00269214 | -8.60062e-05 | -0.00260614 | 32.9611 |
| Mumbai | existing | 0.0698935 | 0.0638885 | 0.000390322 | -0.0019432 | -3.35354e-05 | -0.00158641 | 0.000373554 | -0.00195997 | 19.4232 |

### Dimension: category
| segment | segment_status | baseline_rate | current_rate | mix_effect | rate_effect | cross_term | total_effect | mix_attributed | rate_attributed | contribution_pct |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| skincare | existing | 0.0719581 | 0.0633273 | 7.83919e-05 | -0.00347484 | -9.4025e-06 | -0.00340585 | 7.36906e-05 | -0.00347955 | 41.6994 |
| baby | existing | 0.0762304 | 0.0679325 | -0.000118159 | -0.00269985 | 1.2862e-05 | -0.00280514 | -0.000111728 | -0.00269342 | 34.3446 |
| fitness | existing | 0.0658617 | 0.0585696 | 3.03372e-05 | -0.00198362 | -3.35884e-06 | -0.00195664 | 2.86578e-05 | -0.0019853 | 23.956 |

## 4. Mix / Rate / Cross Decomposition
Ratio and average metrics use the exact identity: total effect = mix effect + rate effect + cross term.

## 5. Investigation Areas
- Investigate channel=paid_search first; it has the largest absolute total_effect signal (-0.004265487581197321).
- Investigate device=mobile first; it has the largest absolute total_effect signal (-0.005193232823200733).
- Investigate city=Bengaluru first; it has the largest absolute total_effect signal (-0.0038890798866961984).
- Investigate category=skincare first; it has the largest absolute total_effect signal (-0.003405854453209873).

## 6. Interpretation Note
MetricLens reports deterministic metric movement decomposition. It identifies segment contributors, mix effects, rate effects, and cross terms. It does not claim causality, statistical significance, anomaly detection, or root cause proof. Use these outputs as investigation signals, not automatic decisions.

## 7. Schema
schema_version: `1.0`
