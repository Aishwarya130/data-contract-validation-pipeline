# Data Dictionary

## Entity: orders
**Grain:** one row per order (`order_id`).
**Primary key:** `order_id`.
**Reference:** `customer_id` must exist in `customers.csv` when reference checking is enabled.

| Column | Type | Nullable | Rule |
|---|---|---:|---|
| order_id | string | No | Unique within each batch; stable producer key |
| customer_id | string | No | Must exist in customer reference data |
| order_ts | timestamp | No | ISO-8601; future timestamps rejected |
| amount | float | No | Must be >= 0 |
| currency | string | No | INR, USD, EUR |
| status | string | No | created, paid, shipped, cancelled, refunded |
| updated_at | timestamp | No | ISO-8601 |
| source_file | string | Yes | Input file provenance; added by pipeline if absent |
| order_date | string | Derived | UTC date derived from order_ts |

## Entity: customers
**Grain:** one row per customer. `customer_id` is the key. The starter generator creates synthetic customer IDs.

## Reject traceability
Every rejected record retains its original fields and has `reject_reason`, with one or more semicolon-separated validation failures. Run-specific output is stored under `data/output/runs/<run_id>/`.
