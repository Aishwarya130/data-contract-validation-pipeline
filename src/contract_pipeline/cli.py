import argparse, json
from pathlib import Path
from .pipeline import run_pipeline
from .generate import generate_dataset
from .contracts import load_contract, compare_schemas

def main():
    parser = argparse.ArgumentParser(description="Validate a producer batch against a versioned data contract.")
    sub = parser.add_subparsers(dest="command", required=True)
    gen = sub.add_parser("generate", help="Generate reproducible synthetic data")
    gen.add_argument("--output", default="data/input/orders.csv")
    gen.add_argument("--rows", type=int, default=100)
    gen.add_argument("--seed", type=int, default=42)
    gen.add_argument("--as-of", default="2026-01-01T00:00:00Z", help="Fixed reference timestamp for reproducible data")
    run = sub.add_parser("run", help="Run validation and publish accepted records")
    run.add_argument("--input", default="data/input/orders.csv")
    run.add_argument("--contract", default="contracts/orders_v1.yaml")
    run.add_argument("--customers", default="data/input/customers.csv")
    run.add_argument("--output-dir", default="data/output")
    run.add_argument("--run-id")
    cmp = sub.add_parser("compare-contracts", help="Compare two YAML contract versions")
    cmp.add_argument("--old", required=True)
    cmp.add_argument("--new", required=True)
    args = parser.parse_args()
    if args.command == "generate":
        generate_dataset(args.output, args.rows, args.seed, as_of=args.as_of)
        print(f"Generated {args.rows} rows at {args.output}")
    elif args.command == "run":
        report = run_pipeline(args.input, args.contract, args.output_dir, args.customers, args.run_id)
        print(json.dumps(report, indent=2))
    elif args.command == "compare-contracts":
        changes = compare_schemas(load_contract(args.old), load_contract(args.new))
        print(json.dumps(changes, indent=2))

if __name__ == "__main__":
    main()
