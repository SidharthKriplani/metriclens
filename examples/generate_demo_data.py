from __future__ import annotations

import itertools
from pathlib import Path

import numpy as np
import pandas as pd


def generate_demo_data(seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2026-04-01", "2026-04-14", freq="D")
    channels = ["paid_search", "organic", "email"]
    devices = ["mobile", "desktop"]
    cities = ["Bengaluru", "Mumbai", "Delhi"]
    categories = ["skincare", "baby", "fitness"]

    rows = []
    for date, channel, device, city, category in itertools.product(
        dates, channels, devices, cities, categories
    ):
        base_sessions = {
            "paid_search": 900,
            "organic": 700,
            "email": 280,
        }[channel]
        base_sessions *= 1.25 if device == "mobile" else 0.80
        base_sessions *= {"Bengaluru": 1.20, "Mumbai": 1.05, "Delhi": 0.95}[city]
        base_sessions *= {"skincare": 1.10, "baby": 0.90, "fitness": 0.75}[category]
        sessions = max(20, int(rng.normal(base_sessions, base_sessions * 0.08)))

        cvr = 0.061
        cvr += {"paid_search": 0.006, "organic": 0.002, "email": 0.012}[channel]
        cvr += 0.004 if device == "desktop" else -0.001
        cvr += {"Bengaluru": 0.004, "Mumbai": 0.001, "Delhi": -0.002}[city]
        cvr += {"skincare": 0.002, "baby": 0.006, "fitness": -0.003}[category]

        # Scripted Movement Mode scenario: current-period paid_search mobile conversion quality weakens.
        if date >= pd.Timestamp("2026-04-08") and channel == "paid_search" and device == "mobile":
            cvr -= 0.020
        # Mix-shift: more current-period traffic flows to paid_search mobile.
        if date >= pd.Timestamp("2026-04-08") and channel == "paid_search" and device == "mobile":
            sessions = int(sessions * 1.28)
        if date >= pd.Timestamp("2026-04-08") and channel == "organic" and device == "desktop":
            sessions = int(sessions * 0.86)

        cvr = float(np.clip(cvr, 0.005, 0.25))
        orders = int(rng.binomial(sessions, cvr))
        aov = {
            "skincare": 1450,
            "baby": 1299,
            "fitness": 999,
        }[category]
        revenue = round(orders * max(300, rng.normal(aov, aov * 0.08)), 2)
        rows.append(
            {
                "date": date.date().isoformat(),
                "channel": channel,
                "device": device,
                "city": city,
                "category": category,
                "sessions": sessions,
                "orders": orders,
                "revenue": revenue,
            }
        )
    return pd.DataFrame(rows)


if __name__ == "__main__":
    out = Path(__file__).resolve().parents[1] / "data" / "ecommerce_demo.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    generate_demo_data().to_csv(out, index=False)
    print(f"Wrote {out}")
