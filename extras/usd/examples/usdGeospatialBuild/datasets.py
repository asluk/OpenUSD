"""Explicitly fetch or import pinned raw datasets into an external cache."""
import argparse
import json
from geobuild.datasets import fetch_public, import_local, inspect_inventory, public_inventory

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("fetch", "import", "inspect"))
    parser.add_argument("--root", required=True)
    parser.add_argument("--dataset")
    parser.add_argument("--source")
    args = parser.parse_args()
    if args.action == "fetch":
        result = fetch_public(args.root)
    elif args.action == "import":
        if not args.dataset or not args.source:
            parser.error("import requires --dataset and --source")
        result = import_local(args.root, args.dataset, args.source)
    else:
        result = public_inventory(inspect_inventory(args.root))
    print(json.dumps(result, indent=2))
