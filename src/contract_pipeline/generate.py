from __future__ import annotations
from pathlib import Path
import random
from datetime import datetime, timedelta, timezone
import pandas as pd

STATUSES = ["created", "paid", "shipped", "cancelled", "refunded"]
CURRENCIES = ["INR", "USD", "EUR"]

def generate_dataset(output_path: str | Path, rows: int = 100, seed: int = 42,
                     inject_edge_cases: bool = True) -> None:
    random.seed(seed)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    data = []
    customers = [f"C{i:05d}" for i in range(max(10, rows // 5))]
    for i in range(rows):
        ts = now - timedelta(days=random.randint(0, 90), minutes=random.randint(0, 1440))
        data.append({
            "order_id": f"O{i:07d}", "customer_id": random.choice(customers),
            "order_ts": ts.isoformat().replace("+00:00", "Z"),
            "amount": round(random.uniform(0, 25000), 2),
            "currency": random.choice(CURRENCIES), "status": random.choice(STATUSES),
            "updated_at": (ts + timedelta(minutes=random.randint(0, 240))).isoformat().replace("+00:00", "Z")
        })
    if inject_edge_cases and rows >= 8:
        data[1]["amount"] = -10
        data[2]["status"] = "in_transit"
        data[3]["customer_id"] = "C_UNKNOWN"
        data[4]["order_id"] = data[0]["order_id"]  # duplicate key
        data[5]["currency"] = None
        data[6]["order_ts"] = (now + timedelta(days=2)).isoformat().replace("+00:00", "Z")
        data[7]["amount"] = "not_a_number"
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(data).to_csv(path, index=False)
    customer_path = path.parent / "customers.csv"
    pd.DataFrame({"customer_id": customers}).to_csv(customer_path, index=False)
