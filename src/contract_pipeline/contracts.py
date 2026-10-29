
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


SUPPORTED_TYPES = {"string", "integer", "float", "boolean", "timestamp"}


def load_contract(path: str | Path) -> dict:
    """Load and validate a data contract from a YAML file."""
    with open(path, "r", encoding="utf-8") as file:
        contract = yaml.safe_load(file)

    if not isinstance(contract, dict):
        raise ValueError("Contract must be a YAML mapping.")

    if not isinstance(contract.get("required_columns"), dict):
        raise ValueError("Contract must define required_columns as a mapping.")

    optional = contract.get("optional_columns", {})
    if not isinstance(optional, dict):
        raise ValueError("optional_columns must be a mapping.")

    required = contract["required_columns"]

    overlap = set(required) & set(optional)
    if overlap:
        raise ValueError(
            f"Columns cannot be both required and optional: {sorted(overlap)}"
        )

    for section_name, columns in (
        ("required_columns", required),
        ("optional_columns", optional),
    ):
        for name, spec in columns.items():
            if not isinstance(spec, dict):
                raise ValueError(
                    f"Specification for column '{name}' must be a mapping."
                )

            column_type = spec.get("type")
            if column_type not in SUPPORTED_TYPES:
                raise ValueError(
                    f"Unsupported type '{column_type}' for column '{name}'."
                )

            if "nullable" in spec and not isinstance(spec["nullable"], bool):
                raise ValueError(
                    f"'nullable' for column '{name}' must be true or false."
                )

            allowed = spec.get("allowed_values")
            if allowed is not None and (
                not isinstance(allowed, list) or not allowed
            ):
                raise ValueError(
                    f"'allowed_values' for column '{name}' must be a non-empty list."
                )

    return contract


def compare_schemas(previous: dict, current: dict) -> list[dict[str, Any]]:
    """Compare two contracts and classify schema changes."""

    old_required = previous.get("required_columns", {})
    old_optional = previous.get("optional_columns", {})
    new_required = current.get("required_columns", {})
    new_optional = current.get("optional_columns", {})

    old_cols = {**old_optional, **old_required}
    new_cols = {**new_optional, **new_required}

    policy = current.get("compatibility", {})
    allow_additive_nullable = policy.get(
        "allow_additive_nullable_columns", True
    )
    breaking_on_removed = policy.get("breaking_on_removed_columns", True)
    breaking_on_type = policy.get("breaking_on_type_change", True)
    breaking_on_nullable_to_required = policy.get(
        "breaking_on_nullable_to_required", True
    )

    changes: list[dict[str, Any]] = []

    def add_change(column, change, severity, detail):
        changes.append({
            "column": column,
            "change": change,
            "severity": severity,
            "detail": detail,
        })

    for name in sorted(old_cols.keys() - new_cols.keys()):
        add_change(
            name,
            "removed_column",
            "breaking" if breaking_on_removed else "non-breaking",
            "A previously defined column was removed.",
        )

    for name in sorted(new_cols.keys() - old_cols.keys()):
        spec = new_cols[name]
        is_required = name in new_required
        nullable = spec.get("nullable", True)

        non_breaking_addition = (
            allow_additive_nullable and nullable
        )

        severity = (
            "non-breaking"
            if non_breaking_addition
            else "breaking"
        )

        detail = (
            "Additive nullable column."
            if non_breaking_addition
            else (
                "New required non-nullable column."
                if is_required and not nullable
                else "New column is not covered by the additive-nullable policy."
            )
        )

        add_change(name, "added_column", severity, detail)

    for name in sorted(old_cols.keys() & new_cols.keys()):
        old = old_cols[name]
        new = new_cols[name]

        if old.get("type") != new.get("type"):
            add_change(
                name,
                "type_changed",
                "breaking" if breaking_on_type else "non-breaking",
                f"Type changed from {old.get('type')} to {new.get('type')}.",
            )

        if old.get("nullable", True) and not new.get("nullable", True):
            add_change(
                name,
                "nullable_to_required",
                "breaking" if breaking_on_nullable_to_required else "non-breaking",
                "Previously nullable column is now non-nullable.",
            )

        was_required = name in old_required
        is_required = name in new_required

        if was_required and not is_required:
            add_change(
                name,
                "required_to_optional",
                "non-breaking",
                "Column changed from required to optional.",
            )
        elif not was_required and is_required:
            add_change(
                name,
                "optional_to_required",
                "breaking",
                "Previously optional column is now required.",
            )

        old_allowed = old.get("allowed_values")
        new_allowed = new.get("allowed_values")

        if old_allowed is not None and new_allowed is not None:
            old_set = set(old_allowed)
            new_set = set(new_allowed)

            removed = old_set - new_set
            added = new_set - old_set

            if removed:
                add_change(
                    name,
                    "allowed_values_removed",
                    "breaking",
                    f"Values removed: {sorted(removed)}",
                )

            if added:
                add_change(
                    name,
                    "allowed_values_added",
                    "non-breaking",
                    f"Values added: {sorted(added)}",
                )

        elif old_allowed is None and new_allowed is not None:
            add_change(
                name,
                "allowed_values_restricted",
                "breaking",
                f"Allowed values are now restricted to: {sorted(new_allowed)}",
            )

        elif old_allowed is not None and new_allowed is None:
            add_change(
                name,
                "allowed_values_unrestricted",
                "non-breaking",
                "Allowed-value restrictions were removed.",
            )

    return changes
