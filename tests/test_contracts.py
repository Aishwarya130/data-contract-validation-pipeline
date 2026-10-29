from contract_pipeline.contracts import compare_schemas

def test_additive_nullable_column_is_non_breaking():
    old = {"required_columns": {"id": {"type": "string", "nullable": False}}}
    new = {"required_columns": {"id": {"type": "string", "nullable": False}},
           "optional_columns": {"note": {"type": "string", "nullable": True}}}
    changes = compare_schemas(old, new)
    assert len(changes) == 1
    assert changes[0]["severity"] == "non-breaking"

def test_type_change_is_breaking():
    old = {"required_columns": {"amount": {"type": "float", "nullable": False}}}
    new = {"required_columns": {"amount": {"type": "string", "nullable": False}}}
    assert compare_schemas(old, new)[0]["severity"] == "breaking"


def test_removed_column_is_breaking():
    old = {"required_columns": {
        "id": {"type": "string", "nullable": False},
        "name": {"type": "string", "nullable": True}
    }}
    new = {"required_columns": {
        "id": {"type": "string", "nullable": False}
    }}

    changes = compare_schemas(old, new)
    assert any(
        c["change"] == "removed_column" and c["severity"] == "breaking"
        for c in changes
    )


def test_nullable_to_required_is_breaking():
    old = {"optional_columns": {
        "note": {"type": "string", "nullable": True}
    }}
    new = {"required_columns": {
        "note": {"type": "string", "nullable": False}
    }}

    changes = compare_schemas(old, new)
    assert any(
        c["change"] == "nullable_to_required"
        and c["severity"] == "breaking"
        for c in changes
    )


def test_added_allowed_value_is_non_breaking():
    old = {"required_columns": {
        "currency": {
            "type": "string", "nullable": False,
            "allowed_values": ["INR", "USD"]
        }
    }}
    new = {"required_columns": {
        "currency": {
            "type": "string", "nullable": False,
            "allowed_values": ["INR", "USD", "EUR"]
        }
    }}

    changes = compare_schemas(old, new)
    assert any(
        c["change"] == "allowed_values_added"
        and c["severity"] == "non-breaking"
        for c in changes
    )


def test_removed_allowed_value_is_breaking():
    old = {"required_columns": {
        "currency": {
            "type": "string", "nullable": False,
            "allowed_values": ["INR", "USD", "EUR"]
        }
    }}
    new = {"required_columns": {
        "currency": {
            "type": "string", "nullable": False,
            "allowed_values": ["INR", "USD"]
        }
    }}

    changes = compare_schemas(old, new)
    assert any(
        c["change"] == "allowed_values_removed"
        and c["severity"] == "breaking"
        for c in changes
    )
