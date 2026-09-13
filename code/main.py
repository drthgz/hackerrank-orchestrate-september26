"""Development entry point: input-only requests, provisional policy, no models."""

import argparse
from pathlib import Path

from buy_or_wait.pipeline import run


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requests", type=Path, required=True, help="Input-only request CSV")
    parser.add_argument("--dataset", type=Path, default=Path(__file__).resolve().parents[1] / "dataset")
    parser.add_argument("--output", type=Path, required=True, help="Development prediction CSV")
    args = parser.parse_args()
    try:
        predictions = run(args.requests, args.dataset, args.output)
    except (ValueError, OSError) as exc:
        parser.exit(2, f"Vertical slice failed; no justified prediction: {exc}\n")
    print(f"Processed: {', '.join(p.request_id for p in predictions)}")
    print("Provisional vertical-slice-v1 forecast; structural validation PASSED")
    print(f"Output: {args.output.resolve()}")


if __name__ == "__main__":
    main()
