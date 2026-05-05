import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

from metriclens import MetricLens, RatioMetric, SumMetric


def test_null_fill_not_modifying_original():
    df = pd.DataFrame(
        [
            {"date": "2026-01-01", "channel": None, "orders": 1, "sessions": 10},
            {"date": "2026-01-02", "channel": "paid", "orders": 1, "sessions": 10},
        ]
    )
    original_nulls = df["channel"].isna().sum()
    MetricLens(df, "date", ("2026-01-01", "2026-01-01"), ("2026-01-02", "2026-01-02"), ["channel"]).analyze(
        RatioMetric("orders", "sessions", name="cvr")
    )
    assert df["channel"].isna().sum() == original_nulls


def test_null_segment_appears_in_output():
    df = pd.DataFrame(
        [
            {"date": "2026-01-01", "channel": None, "revenue": 1},
            {"date": "2026-01-02", "channel": "paid", "revenue": 2},
        ]
    )
    result = MetricLens(df, "date", ("2026-01-01", "2026-01-01"), ("2026-01-02", "2026-01-02"), ["channel"]).analyze(
        SumMetric("revenue")
    )
    segments = {r["segment"] for r in result.to_dict()["dimensions"][0]["segment_contributions"]}
    assert "(null)" in segments


def test_json_valid_and_schema_version():
    df = pd.DataFrame(
        [
            {"date": "2026-01-01", "channel": "a", "orders": 1, "sessions": 10},
            {"date": "2026-01-02", "channel": "a", "orders": 2, "sessions": 10},
        ]
    )
    result = MetricLens(df, "date", ("2026-01-01", "2026-01-01"), ("2026-01-02", "2026-01-02"), ["channel"]).analyze(
        RatioMetric("orders", "sessions", name="cvr")
    )
    payload = json.loads(result.to_json())
    assert payload["schema_version"] == "0.1"
    assert "rate_delta" in payload["dimensions"][0]["segment_contributions"][0]
    forbidden = "rate_delta" + "_pp"
    assert forbidden not in result.to_json()


def test_html_required_sections_and_interpretation_note():
    df = pd.DataFrame(
        [
            {"date": "2026-01-01", "channel": "a", "revenue": 1},
            {"date": "2026-01-02", "channel": "a", "revenue": 2},
        ]
    )
    html = MetricLens(df, "date", ("2026-01-01", "2026-01-01"), ("2026-01-02", "2026-01-02"), ["channel"]).analyze(
        SumMetric("revenue")
    ).to_html()
    for section in [
        "Executive Summary",
        "Data Quality Summary",
        "Segment Contributions",
        "Mix / Rate / Cross Decomposition",
        "Investigation Areas",
        "Interpretation Note",
        "Schema",
    ]:
        assert section in html
    assert "does not claim causality" in html


def test_demo_smoke_runs_and_writes_outputs():
    root = Path(__file__).resolve().parents[1]
    proc = subprocess.run(
        [sys.executable, str(root / "examples" / "ecommerce_demo.py")],
        cwd=root,
        text=True,
        capture_output=True,
        check=True,
    )
    assert "MetricLens ecommerce demo complete" in proc.stdout
    assert (root / "outputs" / "cvr_rca.json").exists()
    assert (root / "outputs" / "cvr_rca.md").exists()
    assert (root / "outputs" / "cvr_rca.html").exists()
