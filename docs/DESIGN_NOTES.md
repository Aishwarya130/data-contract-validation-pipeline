# Design and Trade-offs

- **Local-first:** CSV/YAML/Pandas keeps the solution reproducible without cloud credentials or a database.
- **Contract as configuration:** required and optional columns, types, nullability, allowed values, keys, and business rules live in YAML rather than being scattered through code.
- **Breaking vs non-breaking:** removed columns, type changes, tightening nullability, and removing allowed values are breaking. Additive optional/nullable columns and expanding allowed values are non-breaking for tolerant consumers. A newly required non-null column is breaking.
- **Quarantine instead of silent dropping:** invalid rows are written with source fields and explicit reason codes.
- **Idempotency:** target publishing deduplicates on `order_id`, keeping the latest accepted record for that key. This is suitable for current-state order snapshots; event-history workloads should use immutable event IDs and append-only storage.
- **Run isolation:** each run writes artifacts into its own `runs/<run_id>` directory, while the published target is a current-state view.
- **Limitations:** this is a single-process local prototype, not a distributed scheduler. Schema comparison is intentionally compact and should be extended for nested schemas, semantic version enforcement, and consumer-specific compatibility policies in production.
- **Optimization:** vectorize validation for large datasets and consider Parquet/Polars or a database-backed target when volume and query patterns justify it.
