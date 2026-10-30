from __future__ import annotations
from pathlib import Path
import yaml

def load_contract(path: str | Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        contract = yaml.safe_load(f)
    if not isinstance(contract, dict) or "required_columns" not in contract:
        raise ValueError("Contract must define required_columns")
    return contract

def compare_schemas(previous: dict, current: dict) -> list[dict]:
    """Compare contract versions. Returns classified changes with reasons."""
    old_cols = {**previous.get("required_columns", {}), **previous.get("optional_columns", {})}
    new_cols = {**current.get("required_columns", {}), **current.get("optional_columns", {})}
    changes = []
    for name in sorted(old_cols.keys() - new_cols.keys()):
        changes.append({"column": name, "change": "removed_column", "severity": "breaking",
                        "detail": "A previously defined column was removed."})
    for name in sorted(new_cols.keys() - old_cols.keys()):
        spec = new_cols[name]
        breaking = name in current.get("required_columns", {}) and not spec.get("nullable", True)
        changes.append({"column": name, "change": "added_column",
                        "severity": "breaking" if breaking else "non-breaking",
                        "detail": "New non-null required column." if breaking else "Additive column; compatible for consumers that ignore unknown columns."})
    for name in sorted(old_cols.keys() & new_cols.keys()):
        old, new = old_cols[name], new_cols[name]
        if old.get("type") != new.get("type"):
            changes.append({"column": name, "change": "type_changed", "severity": "breaking",
                            "detail": f"Type changed from {old.get('type')} to {new.get('type')}."})
        if old.get("nullable", True) and not new.get("nullable", True):
            changes.append({"column": name, "change": "nullable_to_required", "severity": "breaking",
                            "detail": "Previously nullable column is now required."})
        old_allowed, new_allowed = set(old.get("allowed_values", [])), set(new.get("allowed_values", []))
        if old_allowed and new_allowed:
            removed, added = old_allowed - new_allowed, new_allowed - old_allowed
            if removed:
                changes.append({"column": name, "change": "allowed_values_removed", "severity": "breaking",
                                "detail": f"Values removed: {sorted(removed)}"})
            if added:
                changes.append({"column": name, "change": "allowed_values_added", "severity": "non-breaking",
                                "detail": f"Values added: {sorted(added)}"})
    return changes
