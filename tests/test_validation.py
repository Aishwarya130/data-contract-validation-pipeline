import pandas as pd
from contract_pipeline.validation import validate_batch

CONTRACT = {
    "primary_key": "order_id",
    "required_columns": {
        "order_id": {"type": "string", "nullable": False},
        "customer_id": {"type": "string", "nullable": False},
        "amount": {"type": "float", "nullable": False},
        "status": {"type": "string", "nullable": False, "allowed_values": ["paid", "created"]}
    },
    "optional_columns": {},
    "business_rules": {"amount_min": 0, "require_customer_reference": True}
}

def test_valid_row_passes():
    df = pd.DataFrame([{"order_id":"O1","customer_id":"C1","amount":10.5,"status":"paid"}])
    accepted, rejected, changes = validate_batch(df, CONTRACT, customers={"C1"})
    assert len(accepted) == 1 and rejected.empty and not changes

def test_invalid_status_and_negative_amount_rejected():
    df = pd.DataFrame([{"order_id":"O1","customer_id":"C1","amount":-1,"status":"in_transit"}])
    accepted, rejected, _ = validate_batch(df, CONTRACT, customers={"C1"})
    assert accepted.empty
    assert "status:value_not_allowed" in rejected.iloc[0]["reject_reason"]
    assert "amount:below_minimum" in rejected.iloc[0]["reject_reason"]

def test_missing_required_column_quarantines_batch():
    df = pd.DataFrame([{"order_id":"O1","amount":5}])
    accepted, rejected, changes = validate_batch(df, CONTRACT)
    assert accepted.empty and len(rejected) == 1
    assert any(c["severity"] == "breaking" for c in changes)

def test_duplicate_key_is_rejected():
    df = pd.DataFrame([
        {"order_id":"O1","customer_id":"C1","amount":1,"status":"paid"},
        {"order_id":"O1","customer_id":"C1","amount":2,"status":"paid"}
    ])
    accepted, rejected, _ = validate_batch(df, CONTRACT, customers={"C1"})
    assert len(accepted) == 1 and len(rejected) == 1
    assert "duplicate_key_in_batch" in rejected.iloc[0]["reject_reason"]

def test_unknown_customer_is_rejected():
    df = pd.DataFrame([{"order_id":"O1","customer_id":"UNKNOWN","amount":1,"status":"paid"}])
    accepted, rejected, _ = validate_batch(df, CONTRACT, customers={"C1"})
    assert accepted.empty and "unknown_reference" in rejected.iloc[0]["reject_reason"]

def test_empty_batch():
    df = pd.DataFrame(columns=["order_id","customer_id","amount","status"])
    accepted, rejected, _ = validate_batch(df, CONTRACT, customers={"C1"})
    assert accepted.empty and rejected.empty

def test_invalid_first_duplicate_does_not_block_later_valid_row():
    df = pd.DataFrame([
        {"order_id":"O1","customer_id":"UNKNOWN","amount":1,"status":"paid"},
        {"order_id":"O1","customer_id":"C1","amount":2,"status":"paid"}
    ])
    accepted, rejected, _ = validate_batch(df, CONTRACT, customers={"C1"})
    assert len(accepted) == 1
    assert len(rejected) == 1
    assert "unknown_reference" in rejected.iloc[0]["reject_reason"]

def test_unexpected_column_is_reported_non_breaking():
    df = pd.DataFrame([{"order_id":"O1","customer_id":"C1","amount":1,"status":"paid","extra":"x"}])
    accepted, rejected, changes = validate_batch(df, CONTRACT, customers={"C1"})
    assert len(accepted) == 1 and rejected.empty
    assert any(c["change"] == "unexpected_column" and c["severity"] == "non-breaking" for c in changes)

def test_out_of_order_timestamps_are_validated_without_reordering():
    df = pd.DataFrame([
        {"order_id":"O2","customer_id":"C1","amount":1,"status":"paid"},
        {"order_id":"O1","customer_id":"C1","amount":1,"status":"paid"}
    ])
    accepted, rejected, _ = validate_batch(df, CONTRACT, customers={"C1"})
    assert accepted["order_id"].tolist() == ["O2", "O1"]
    assert rejected.empty


def test_future_order_timestamp_is_rejected():
    from datetime import datetime, timezone
    contract = {
        **CONTRACT,
        "required_columns": {
            **CONTRACT["required_columns"],
            "order_ts": {"type": "timestamp", "nullable": False}
        },
        "business_rules": {
            **CONTRACT["business_rules"],
            "reject_future_order_ts": True
        }
    }
    df = pd.DataFrame([{
        "order_id": "O-FUTURE", "customer_id": "C1", "amount": 10,
        "status": "paid", "order_ts": "2026-02-01T00:00:00Z"
    }])
    fixed_now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    accepted, rejected, _ = validate_batch(df, contract, customers={"C1"}, now=fixed_now)
    assert accepted.empty
    assert "order_ts:future_timestamp" in rejected.iloc[0]["reject_reason"]


def test_null_required_field_is_rejected():
    df = pd.DataFrame([{
        "order_id": "O-NULL", "customer_id": "C1",
        "amount": 10, "status": None
    }])
    accepted, rejected, _ = validate_batch(df, CONTRACT, customers={"C1"})
    assert accepted.empty
    assert "status:null_not_allowed" in rejected.iloc[0]["reject_reason"]
