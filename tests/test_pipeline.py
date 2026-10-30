import json
from pathlib import Path
import pandas as pd
import pytest
from contract_pipeline.generate import generate_dataset
from contract_pipeline.pipeline import run_pipeline

def test_generator_is_reproducible(tmp_path):
    a, b = tmp_path / "a/orders.csv", tmp_path / "b/orders.csv"
    generate_dataset(a, rows=20, seed=7)
    generate_dataset(b, rows=20, seed=7)
    assert a.read_bytes() == b.read_bytes()

def test_pipeline_empty_batch(tmp_path):
    input_path = tmp_path / "empty.csv"
    pd.DataFrame(columns=["order_id","customer_id","order_ts","amount","currency","status","updated_at"]).to_csv(input_path, index=False)
    customers = tmp_path / "customers.csv"
    pd.DataFrame({"customer_id": ["C1"]}).to_csv(customers, index=False)
    contract = Path(__file__).parents[1] / "contracts" / "orders_v1.yaml"
    report = run_pipeline(input_path, contract, tmp_path / "out", customers, "empty-run")
    assert report["input_rows"] == report["accepted_rows"] == report["rejected_rows"] == 0
    assert report["reconciliation"]["input_equals_accepted_plus_rejected"]

def test_malformed_input_writes_failure_report(tmp_path):
    bad = tmp_path / "bad.txt"
    bad.write_text("not a supported input format", encoding="utf-8")
    contract = Path(__file__).parents[1] / "contracts" / "orders_v1.yaml"
    with pytest.raises(ValueError):
        run_pipeline(bad, contract, tmp_path / "out", run_id="bad-run")
    report = json.loads((tmp_path / "out/runs/bad-run/run_report.json").read_text())
    assert report["status"] == "failed"
    assert "Supported input formats" in report["failure_reason"]

def test_same_batch_rerun_does_not_duplicate_target(tmp_path):
    input_path = tmp_path / "orders.csv"
    generate_dataset(input_path, rows=20, seed=9)
    customers = tmp_path / "customers.csv"
    contract = Path(__file__).parents[1] / "contracts" / "orders_v1.yaml"
    out = tmp_path / "out"
    run_pipeline(input_path, contract, out, customers, "first")
    first = pd.read_csv(out / "orders_target.csv")
    run_pipeline(input_path, contract, out, customers, "second")
    second = pd.read_csv(out / "orders_target.csv")
    assert len(first) == len(second)
    assert second["order_id"].is_unique
    assert second["run_id"].eq("second").all()


def test_malformed_json_lines_writes_failure_report(tmp_path):
    bad = tmp_path / "malformed.json"
    bad.write_text('{"order_id": "O1"}\\n{this is not valid json}\\n', encoding="utf-8")
    contract = Path(__file__).parents[1] / "contracts" / "orders_v1.yaml"
    with pytest.raises(ValueError):
        run_pipeline(bad, contract, tmp_path / "out", run_id="malformed-json")
    report = json.loads((tmp_path / "out/runs/malformed-json/run_report.json").read_text())
    assert report["status"] == "failed"
    assert report["failure_reason"]
