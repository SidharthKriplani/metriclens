from __future__ import annotations

from pathlib import Path

from generate_demo_data import generate_demo_data
from metriclens import MetricLens, RatioMetric, SumMetric


ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = ROOT / "outputs"


def main() -> None:
    df = generate_demo_data(seed=42)
    data_path = ROOT / "data" / "ecommerce_demo.csv"
    data_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(data_path, index=False)

    lens = MetricLens(
        data=df,
        date_col="date",
        baseline_period=("2026-04-01", "2026-04-07"),
        current_period=("2026-04-08", "2026-04-14"),
        dimensions=["channel", "device", "city", "category"],
    )

    cvr_result = lens.analyze(RatioMetric("orders", "sessions", name="cvr"))
    OUTPUTS.mkdir(exist_ok=True)
    cvr_result.to_json(OUTPUTS / "cvr_rca.json")
    cvr_result.to_markdown(OUTPUTS / "cvr_rca.md")
    cvr_result.to_html(OUTPUTS / "cvr_rca.html")

    revenue_result = lens.analyze(SumMetric("revenue", name="revenue"))
    revenue_result.to_json(OUTPUTS / "revenue_rca.json")
    revenue_result.to_markdown(OUTPUTS / "revenue_rca.md")
    revenue_result.to_html(OUTPUTS / "revenue_rca.html")

    summary = cvr_result.summary()
    print("MetricLens ecommerce demo complete")
    print(f"Rows: {len(df)}")
    print(f"CVR baseline: {summary['baseline_value']:.4f}")
    print(f"CVR current:  {summary['current_value']:.4f}")
    print(f"CVR delta:    {summary['absolute_delta']:.4f}")
    print("Outputs: outputs")


if __name__ == "__main__":
    main()
