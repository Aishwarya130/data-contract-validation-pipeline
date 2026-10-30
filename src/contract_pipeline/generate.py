from __future__ import annotations
from pathlib import Path
import random
from datetime import datetime, timedelta, timezone
import pandas as pd

STATUSES = ["created", "paid", "shipped", "cancelled", "refunded"]

def generate_dataset(output_path: str | Path, rows: int = 100, seed: int = 42,
                     inject_edge_cases: bool = True,
                     as_of: datetime | str = "2026-01-01T00:00:00Z") -> None:
    """Generate repeatable synthetic orders using both a fixed seed and reference time."""
    rng = random.Random(seed)
    if isinstance(as_of, str):
        now = pd.Timestamp(as_of).to_pydatetime()
    else:
        now = as_of
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    now = now.astimezone(timezone.utc).replace(microsecond=0)
    data = []
    customers = [f"C{i:05d}" for i in range(max(10, rows // 5))]
    for i in range(rows):
        ts = now - timedelta(days=rng.randint(0, 90), minutes=rng.randint(0, 1440))
        data.append({
            "order_id": f"O{i:07d}", "customer_id": rng.choice(customers),
            "order_ts": ts.isoformat().replace("+00:00", "Z"),
            "amount": round(rng.uniform(0, 25000), 2),
            "currency": rng.choice(["INR", "USD", "EUR"]),
            "status": rng.choice(STATUSES),
            "updated_at": (ts + timedelta(minutes=rng.randint(0, 240))).isoformat().replace("+00:00", "Z")
        })
    if inject_edge_cases and rows >= 8:
        data[1]["amount"] = -10
        data[2]["status"] = "in_transit"
        data[3]["customer_id"] = "C_UNKNOWN"
        data[4]["order_id"] = data[0]["order_id"]
        data[5]["currency"] = None
        data[6]["order_ts"] = "2099-01-01T00:00:00Z"  # deliberately future-dated test record
        data[7]["amount"] = "not_a_number"
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(data).to_csv(path, index=False)
    customer_path = path.parent / "customers.csv"
    pd.DataFrame({"customer_id": customers}).to_csv(customer_path, index=False)
