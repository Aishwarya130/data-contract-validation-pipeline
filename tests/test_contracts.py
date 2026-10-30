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
    old = {"required_columns": {"id": {"type": "string"}, "name": {"type": "string"}}}
    new = {"required_columns": {"id": {"type": "string"}}}
    assert compare_schemas(old, new)[0]["severity"] == "breaking"

def test_expanded_allowed_values_is_non_breaking():
    old = {"required_columns": {"status": {"type": "string", "allowed_values": ["paid"]}}}
    new = {"required_columns": {"status": {"type": "string", "allowed_values": ["paid", "shipped"]}}}
    assert compare_schemas(old, new)[0]["severity"] == "non-breaking"
