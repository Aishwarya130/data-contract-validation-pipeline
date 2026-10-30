from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import json, time, uuid
import pandas as pd
from .contracts import load_contract
from .validation import validate_batch

def _read_input(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".json":
        return pd.read_json(path, lines=True)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path, dtype={"order_id": "string", "customer_id": "string", "currency": "string", "status": "string"})
    raise ValueError("Supported input formats are .csv and line-delimited .json")

def run_pipeline(input_path: str | Path, contract_path: str | Path, output_dir: str | Path,
                 customers_path: str | Path | None = None, run_id: str | None = None) -> dict:
    start = datetime.now(timezone.utc)
    started = time.perf_counter()
    run_id = run_id or str(uuid.uuid4())
    input_path, output_dir = Path(input_path), Path(output_dir)
    run_dir = output_dir / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    report_path = run_dir / "run_report.json"
    base_report = {
        "run_id": run_id, "status": "running", "started_at": start.isoformat(),
        "input_file": input_path.name, "input_rows": 0, "accepted_rows": 0,
        "rejected_rows": 0, "schema_change_count": 0, "schema_changes": [],
        "target_rows_after_publish": None
    }
    try:
        contract = load_contract(contract_path)
        df = _read_input(input_path)
        base_report["input_rows"] = int(len(df))
        customers = None
        if customers_path:
            customer_df = pd.read_csv(customers_path, dtype={"customer_id": "string"})
            if "customer_id" not in customer_df.columns:
                raise ValueError("Customer reference file must contain customer_id")
            customers = set(customer_df["customer_id"].dropna().astype(str))
        if "source_file" not in df.columns:
            df["source_file"] = input_path.name

        accepted, rejected, schema_changes = validate_batch(df, contract, customers=customers)
        # Attach run lineage to both accepted and rejected records.
        accepted["run_id"] = run_id
        rejected["run_id"] = run_id
        if not accepted.empty:
            accepted["order_ts"] = pd.to_datetime(accepted["order_ts"], utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            accepted["updated_at"] = pd.to_datetime(accepted["updated_at"], utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            accepted["amount"] = pd.to_numeric(accepted["amount"]).round(2)
            accepted["order_date"] = pd.to_datetime(accepted["order_ts"], utc=True).dt.strftime("%Y-%m-%d")
        accepted_path = run_dir / "accepted_orders.csv"
        rejected_path = run_dir / "quarantine.csv"
        schema_path = run_dir / "schema_changes.json"
        accepted.to_csv(accepted_path, index=False)
        rejected.to_csv(rejected_path, index=False)
        schema_path.write_text(json.dumps(schema_changes, indent=2), encoding="utf-8")

        target_path = output_dir / "orders_target.csv"
        if target_path.exists():
            prior = pd.read_csv(target_path, dtype={"order_id": "string"})
            combined = pd.concat([prior, accepted], ignore_index=True)
            combined = combined.drop_duplicates(subset=["order_id"], keep="last")
        else:
            combined = accepted.copy()
        combined.to_csv(target_path, index=False)

        elapsed = round(time.perf_counter() - started, 4)
        ended = datetime.now(timezone.utc)
        breaking = any(item["severity"] == "breaking" for item in schema_changes)
        report = {
            **base_report,
            "status": "completed_with_schema_break" if breaking else "success",
            "ended_at": ended.isoformat(), "accepted_rows": int(len(accepted)),
            "rejected_rows": int(len(rejected)), "schema_change_count": len(schema_changes),
            "schema_changes": schema_changes, "target_rows_after_publish": int(len(combined)),
            "elapsed_seconds": elapsed,
            "rows_per_second": round(len(df) / elapsed, 2) if elapsed > 0 else None,
            "reconciliation": {
                "input_equals_accepted_plus_rejected": len(df) == len(accepted) + len(rejected),
                "target_primary_key_unique": bool(combined["order_id"].is_unique) if "order_id" in combined else True
            },
            "artifacts": {"accepted": str(accepted_path), "quarantine": str(rejected_path),
                          "schema_changes": str(schema_path), "target": str(target_path)}
        }
        report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        return report
    except Exception as exc:
        elapsed = round(time.perf_counter() - started, 4)
        failed = {
            **base_report, "status": "failed", "ended_at": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": elapsed, "failure_reason": f"{type(exc).__name__}: {exc}"
        }
        report_path.write_text(json.dumps(failed, indent=2), encoding="utf-8")
        raise
