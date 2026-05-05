from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
from jinja2 import Template

from metriclens.exceptions import DecompositionTypeError

MANDATORY_INTERPRETATION_NOTE = (
    "MetricLens reports deterministic metric movement decomposition. It identifies segment "
    "contributors, mix effects, rate effects, and cross terms. It does not claim causality, "
    "statistical significance, anomaly detection, or root cause proof. Use these outputs as "
    "investigation signals, not automatic decisions."
)


@dataclass
class AnalysisResult:
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return self.payload

    def to_json(self, path: str | Path | None = None, *, indent: int = 2) -> str:
        text = json.dumps(self.payload, indent=indent, default=_json_default)
        if path is not None:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_text(text + "\n", encoding="utf-8")
        return text

    def to_markdown(self, path: str | Path | None = None) -> str:
        text = self._build_markdown()
        if path is not None:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_text(text + "\n", encoding="utf-8")
        return text

    def to_html(self, path: str | Path | None = None) -> str:
        text = self._build_html()
        if path is not None:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            Path(path).write_text(text + "\n", encoding="utf-8")
        return text

    def summary(self) -> dict[str, Any]:
        return self.payload["executive_summary"]

    def segment_contributions(self) -> pd.DataFrame:
        rows = []
        for dimension in self.payload["dimensions"]:
            rows.extend(dimension["segment_contributions"])
        return pd.DataFrame(rows)

    def cross_dimension_interactions(self) -> dict[str, Any] | None:
        """Return the cross-dimension interaction payload if available (requires ≥2 dimensions)."""
        return self.payload.get("cross_dimension_interactions")

    def mix_shift(self) -> pd.DataFrame:
        if self.payload["metadata"]["decomposition_type"] != "ratio":
            raise DecompositionTypeError("mix_shift() is only available for RatioMetric and AverageMetric results.")
        rows = []
        for dimension in self.payload["dimensions"]:
            rows.extend(dimension["segment_contributions"])
        return pd.DataFrame(rows)

    def _build_markdown(self) -> str:
        summary = self.payload["executive_summary"]
        metric = self.payload["metadata"]["metric_name"]
        lines = [
            f"# MetricLens Report: {metric}",
            "",
            "## 1. Executive Summary",
            f"- Baseline value: `{summary['baseline_value']}`",
            f"- Current value: `{summary['current_value']}`",
            f"- Absolute delta: `{summary['absolute_delta']}`",
            f"- Relative delta pct: `{summary['relative_delta_pct']}`",
            f"- Direction: `{summary['direction']}`",
            "",
            "## 2. Data Quality Summary",
        ]
        for check in self.payload["quality_checks"]:
            lines.append(f"- **{check['status']}** `{check['check']}` — {check['detail']}")
        lines.extend(["", "## 3. Segment Contributions"])
        for dimension in self.payload["dimensions"]:
            lines.append(f"\n### Dimension: {dimension['dimension']}")
            rows = dimension["segment_contributions"][:10]
            if not rows:
                lines.append("No segment rows.")
                continue
            lines.append(_markdown_table(rows))
        lines.extend(["", "## 4. Mix / Rate / Cross Decomposition"])
        if self.payload["metadata"]["decomposition_type"] == "ratio":
            lines.append("Ratio and average metrics use the exact identity: total effect = mix effect + rate effect + cross term.")
        else:
            lines.append("Not applicable for additive metrics.")
        lines.extend(["", "## 5. Investigation Areas"])
        for item in self.payload["investigation_areas"]:
            lines.append(f"- {item}")
        lines.extend([
            "",
            "## 6. Interpretation Note",
            self.payload["interpretation_note"],
            "",
            "## 7. Schema",
            f"schema_version: `{self.payload['schema_version']}`",
        ])
        return "\n".join(lines)

    def _build_html(self) -> str:
        template = Template(
            """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>MetricLens Report - {{ metric }}</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 32px; line-height: 1.45; color: #222; }
    table { border-collapse: collapse; width: 100%; margin: 12px 0 28px; font-size: 13px; }
    th, td { border: 1px solid #ddd; padding: 6px 8px; text-align: left; }
    th { background: #f5f5f5; }
    code { background: #f5f5f5; padding: 2px 4px; border-radius: 4px; }
    .note { background: #fff8dc; padding: 12px; border-left: 4px solid #d2a106; }
  </style>
</head>
<body>
<h1>MetricLens Report: {{ metric }}</h1>
<h2>1. Executive Summary</h2>
<ul>
<li>Baseline value: <code>{{ summary.baseline_value }}</code></li>
<li>Current value: <code>{{ summary.current_value }}</code></li>
<li>Absolute delta: <code>{{ summary.absolute_delta }}</code></li>
<li>Relative delta pct: <code>{{ summary.relative_delta_pct }}</code></li>
<li>Direction: <code>{{ summary.direction }}</code></li>
</ul>
<h2>2. Data Quality Summary</h2>
<ul>{% for check in checks %}<li><strong>{{ check.status }}</strong> <code>{{ check.check }}</code> — {{ check.detail }}</li>{% endfor %}</ul>
<h2>3. Segment Contributions</h2>
{% for dimension in dimensions %}
<h3>Dimension: {{ dimension.dimension }}</h3>
{{ tables[loop.index0] }}
{% endfor %}
<h2>4. Mix / Rate / Cross Decomposition</h2>
<p>{% if decomp == 'ratio' %}Ratio and average metrics use the exact identity: total effect = mix effect + rate effect + cross term.{% else %}Not applicable for additive metrics.{% endif %}</p>
<h2>5. Investigation Areas</h2>
<ul>{% for item in investigation_areas %}<li>{{ item }}</li>{% endfor %}</ul>
<h2>6. Interpretation Note</h2>
<p class="note">{{ note }}</p>
<h2>7. Schema</h2>
<p>schema_version: <code>{{ schema_version }}</code></p>
</body>
</html>
""".strip()
        )
        tables = []
        for dimension in self.payload["dimensions"]:
            df = pd.DataFrame(dimension["segment_contributions"][:10])
            tables.append(df.to_html(index=False, border=0) if not df.empty else "<p>No segment rows.</p>")
        return template.render(
            metric=self.payload["metadata"]["metric_name"],
            summary=self.payload["executive_summary"],
            checks=self.payload["quality_checks"],
            dimensions=self.payload["dimensions"],
            tables=tables,
            decomp=self.payload["metadata"]["decomposition_type"],
            investigation_areas=self.payload["investigation_areas"],
            note=self.payload["interpretation_note"],
            schema_version=self.payload["schema_version"],
        )


def _markdown_table(rows: list[dict[str, Any]]) -> str:
    # Keep reports readable by limiting wide tables to the most useful v0 columns.
    preferred = [
        "segment",
        "segment_status",
        "baseline_value",
        "current_value",
        "segment_delta",
        "baseline_rate",
        "current_rate",
        "mix_effect",
        "rate_effect",
        "cross_term",
        "total_effect",
        "contribution_pct",
    ]
    columns = [c for c in preferred if c in rows[0]]
    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join(["---"] * len(columns)) + " |"
    body = []
    for row in rows:
        body.append("| " + " | ".join(_fmt(row.get(c)) for c in columns) + " |")
    return "\n".join([header, sep, *body])


def _fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def _json_default(obj: Any) -> Any:
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")
