from __future__ import annotations
from datetime import datetime, timezone
import pandas as pd

def _type_ok(value, kind: str) -> bool:
    if pd.isna(value):
        return True
    if kind == "string":
        return isinstance(value, str)
    if kind == "integer":
        try:
            return float(value).is_integer()
        except (ValueError, TypeError):
            return False
    if kind == "float":
        try:
            return pd.notna(float(value))
        except (ValueError, TypeError):
            return False
    if kind == "timestamp":
        try:
            pd.to_datetime(value, utc=True, errors="raise")
            return True
        except (ValueError, TypeError, OverflowError):
            return False
    if kind == "boolean":
        return str(value).lower() in {"true", "false", "1", "0"}
    return False

def validate_batch(df: pd.DataFrame, contract: dict, customers: set[str] | None = None,
                   now: datetime | None = None) -> tuple[pd.DataFrame, pd.DataFrame, list[dict]]:
    """Return accepted rows, quarantined rows, and input-schema change report."""
    required = contract.get("required_columns", {})
    optional = contract.get("optional_columns", {})
    schema_changes = []
    missing = sorted(set(required) - set(df.columns))
    unexpected = sorted(set(df.columns) - set(required) - set(optional))
    for col in missing:
        schema_changes.append({"column": col, "change": "missing_required_column", "severity": "breaking",
                               "detail": "Required contract column is absent from input."})
    for col in unexpected:
        schema_changes.append({"column": col, "change": "unexpected_column", "severity": "non-breaking",
                               "detail": "Input contains a column not declared in the contract."})
    if missing:
        rejected = df.copy()
        rejected["reject_reason"] = "missing_required_column:" + ",".join(missing)
        return df.iloc[0:0].copy(), rejected, schema_changes

    data = df.copy().reset_index(drop=True)
    if "source_file" not in data.columns:
        data["source_file"] = "unknown"
    reasons: list[list[str]] = [[] for _ in range(len(data))]
    now = now or datetime.now(timezone.utc)

    for pos, (_, row) in enumerate(data.iterrows()):
        for col, spec in {**required, **optional}.items():
            if col not in data.columns:
                continue
            value = row[col]
            if pd.isna(value) or (isinstance(value, str) and value.strip() == ""):
                if not spec.get("nullable", True):
                    reasons[pos].append(f"{col}:null_not_allowed")
                continue
            if not _type_ok(value, spec.get("type", "")):
                reasons[pos].append(f"{col}:invalid_type_expected_{spec.get('type')}")
                continue
            allowed = spec.get("allowed_values")
            if allowed and value not in allowed:
                reasons[pos].append(f"{col}:value_not_allowed")

        rules = contract.get("business_rules", {})
        if "amount" in data.columns and pd.notna(row.get("amount")):
            try:
                if float(row["amount"]) < float(rules.get("amount_min", 0)):
                    reasons[pos].append("amount:below_minimum")
            except (ValueError, TypeError):
                pass
        if rules.get("require_customer_reference") and customers is not None:
            if pd.notna(row.get("customer_id")) and str(row.get("customer_id")) not in customers:
                reasons[pos].append("customer_id:unknown_reference")
        if rules.get("reject_future_order_ts") and pd.notna(row.get("order_ts")):
            try:
                ts = pd.to_datetime(row["order_ts"], utc=True, errors="raise")
                if ts.to_pydatetime() > now:
                    reasons[pos].append("order_ts:future_timestamp")
            except (ValueError, TypeError, OverflowError):
                pass

    # Only valid rows reserve a primary key. An invalid first occurrence must not
    # cause a later valid record with the same key to be rejected.
    pk = contract.get("primary_key")
    seen: set[str] = set()
    for pos, row in data.iterrows():
        key_value = row.get(pk) if pk else None
        if pd.isna(key_value):
            continue
        key = str(key_value)
        if key in seen:
            reasons[pos].append(f"{pk}:duplicate_key_in_batch")
        elif not reasons[pos]:
            seen.add(key)

    data["reject_reason"] = [";".join(items) for items in reasons]
    rejected = data[data["reject_reason"] != ""].copy()
    accepted = data[data["reject_reason"] == ""].copy()
    return accepted, rejected, schema_changes
