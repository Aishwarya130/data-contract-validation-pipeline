# Data Contract Validation & Reliable ETL Pipeline

A local-first data engineering project that validates producer batches against a versioned YAML contract, quarantines invalid rows, publishes accepted records idempotently, and emits run-level operational metrics.

## Features
- Contract fields: required/optional columns, types, nullability, allowed values, primary key, and business rules.
- Compatibility report distinguishes breaking and non-breaking schema changes.
- Record-level validation and explicit quarantine reason codes.
- Primary-key duplicate checks and customer referential integrity.
- Deterministic derived `order_date`, run ID, timestamps, counts, throughput, and JSON report.
- Reproducible synthetic data generator with a fixed random seed.
- Automated tests for happy path, empty input, missing columns, duplicates, invalid values, unknown references, unexpected columns, schema compatibility, deterministic generation, failed-run reporting, out-of-order records, and reruns.
- Idempotent target publish keyed by `order_id`.

## Requirements
Python 3.10 or newer.

## Setup
```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate

python -m pip install --upgrade pip
pip install -e ".[dev]"
```

## Quick start
Generate a 100-row sample and a matching synthetic customer reference file:
```bash
contract-pipeline generate --output data/input/orders.csv --rows 100 --seed 42 --as-of 2026-01-01T00:00:00Z
```

Run the pipeline:
```bash
contract-pipeline run --input data/input/orders.csv --contract contracts/orders_v1.yaml --customers data/input/customers.csv --output-dir data/output --run-id demo-001
```

Generate a larger batch:
```bash
contract-pipeline generate --output data/input/orders_100k.csv --rows 100000 --seed 42 --as-of 2026-01-01T00:00:00Z
contract-pipeline run --input data/input/orders_100k.csv --contract contracts/orders_v1.yaml --customers data/input/customers.csv --output-dir data/output --run-id scale-100k
```

Run automated tests:
```bash
pytest -q
```

## Output artifacts
Each run writes to `data/output/runs/<run_id>/`:
- `accepted_orders.csv`: accepted records plus deterministic derived field `order_date` and `run_id` lineage.
- `quarantine.csv`: rejected records, `reject_reason`, and `run_id` lineage.
- `schema_changes.json`: missing/unexpected schema columns and severity.
- `run_report.json`: run status, input/accepted/rejected counts, timing, throughput, and artifact paths.

The current-state published target is `data/output/orders_target.csv`. Publishing is idempotent by `order_id`: a repeated key replaces the previous target row instead of adding another copy.

## Included example artifacts
A reproducible 100-row input sample is included under `examples/sample_input/`. A completed example run, including accepted rows, quarantine, schema-change report, and run report, is included under `examples/sample_output/`.

## Contract compatibility policy
Use `compare-contracts` to compare contract versions:
```bash
contract-pipeline compare-contracts --old contracts/orders_v1.yaml --new contracts/orders_v2.yaml
```
Breaking examples: removed columns, changed types, nullable-to-required, removal of an allowed value, adding a required non-null column.
Non-breaking examples: adding an optional/nullable column, expanding allowed values. Consumers should ignore unknown fields to benefit from additive compatibility.

## Architecture
Producer CSV/JSON -> YAML contract and schema check -> row validation -> accepted transformation -> target publish.
Invalid records -> quarantine with reasons.
Every run -> schema report and operational JSON report.

## Recovery and reruns
Use a stable `--run-id` to make a run's artifacts easy to locate. Failed runs also write `run_report.json` with status and failure reason before the error is raised to the caller. Each run writes to its own run directory. Re-running the same input is safe for target uniqueness because publish is keyed by `order_id`. For backfills, use a distinct run ID and retain the original input file; inspect the run report and quarantine before publishing downstream.

## Security
Only synthetic data is included. Do not commit secrets, access tokens, credentials, or sensitive real customer data.

## Reproducibility and reconciliation
The generator uses a local seeded random-number generator and a fixed `--as-of` timestamp, so the same seed, row count, and reference timestamp produce byte-identical CSV output. The run report includes reconciliation assertions for input = accepted + rejected and target primary-key uniqueness.

## Known limitations
- Local, single-process execution; no orchestration or distributed processing.
- The compact schema compatibility checker compares contract definitions, while the batch validator checks input schema against the active contract.
- Current-state order target is used; event-sourced history would require an immutable event key and append-only table.
- Type validation is designed for common CSV input and can be strengthened for strict source-format enforcement.
