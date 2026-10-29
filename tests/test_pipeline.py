
import pandas as pd

from contract_pipeline.pipeline import run_pipeline


def create_input(path, amount, updated_at):
    pd.DataFrame([{
        "order_id": "O1",
        "customer_id": "C1",
        "order_ts": "2026-01-01T10:00:00Z",
        "amount": amount,
        "currency": "INR",
        "status": "paid",
        "updated_at": updated_at,
    }]).to_csv(path, index=False)


def create_contract(path):
    path.write_text("""
contract_name: orders
version: 1
primary_key: order_id
required_columns:
  order_id: {type: string, nullable: false}
  customer_id: {type: string, nullable: false}
  order_ts: {type: timestamp, nullable: false}
  amount: {type: float, nullable: false}
  currency:
    type: string
    nullable: false
    allowed_values: [INR, USD, EUR]
  status:
    type: string
    nullable: false
    allowed_values: [created, paid, shipped, cancelled, refunded]
  updated_at: {type: timestamp, nullable: false}
optional_columns:
  source_file: {type: string, nullable: true}
compatibility:
  allow_additive_nullable_columns: true
  breaking_on_removed_columns: true
  breaking_on_type_change: true
  breaking_on_nullable_to_required: true
business_rules:
  amount_min: 0
  require_customer_reference: false
  reject_future_order_ts: false
""", encoding="utf-8")


def test_older_record_does_not_overwrite_newer_record(tmp_path):
    contract = tmp_path / "contract.yaml"
    output = tmp_path / "output"
    newer = tmp_path / "newer.csv"
    older = tmp_path / "older.csv"

    create_contract(contract)
    create_input(newer, 200, "2026-01-02T10:00:00Z")
    create_input(older, 100, "2026-01-01T10:00:00Z")

    run_pipeline(newer, contract, output, run_id="newer")
    run_pipeline(older, contract, output, run_id="older")

    target = pd.read_csv(output / "orders_target.csv")

    assert len(target) == 1
    assert target.iloc[0]["amount"] == 200


def test_rerunning_same_input_does_not_duplicate_orders(tmp_path):
    contract = tmp_path / "contract.yaml"
    output = tmp_path / "output"
    source = tmp_path / "orders.csv"

    create_contract(contract)
    create_input(source, 200, "2026-01-02T10:00:00Z")

    run_pipeline(source, contract, output, run_id="first-run")
    run_pipeline(source, contract, output, run_id="second-run")

    target = pd.read_csv(output / "orders_target.csv")

    assert len(target) == 1
    assert target["order_id"].is_unique

def test_malformed_csv_fails_clearly(tmp_path):
    import pytest
    from contract_pipeline.pipeline import _read_input

    malformed = tmp_path / "malformed.csv"
    malformed.write_text(
        'order_id,customer_id,amount\n'
        'O1,C1,"unfinished quote\n',
        encoding="utf-8"
    )

    with pytest.raises((ValueError, pd.errors.ParserError)):
        _read_input(malformed)