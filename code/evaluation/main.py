"""Local sample evaluation; no changes to the financial engine or model calls."""

import argparse
import json
from decimal import Decimal
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from buy_or_wait.forecast import ForecastPolicy
from evaluation.runner import evaluate


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--request-id", action="append", help="Repeat for multiple IDs")
    selection.add_argument("--subset", choices=["smoke"])
    selection.add_argument("--all", action="store_true", dest="all_samples")
    root = Path(__file__).resolve().parents[2]
    parser.add_argument("--dataset", type=Path, default=root / "dataset")
    parser.add_argument("--artifact-root", type=Path, default=root / "artifacts" / "evaluation")
    parser.add_argument("--run-id", help="Optional unique run directory name; existing runs are never overwritten")
    parser.add_argument("--policy-config", type=Path, help="Optional ForecastPolicy JSON overrides for separate configuration runs")
    parser.add_argument("--extraction-mode", choices=["disabled", "deterministic-only", "cached", "live"],
                        default="disabled")
    args = parser.parse_args()
    try:
        config = json.loads(args.policy_config.read_text(), parse_float=Decimal) if args.policy_config else {}
        if "max_relative_amount_deviation" in config:
            config["max_relative_amount_deviation"] = Decimal(str(config["max_relative_amount_deviation"]))
        if "fixed_intervals" in config:
            config["fixed_intervals"] = tuple(config["fixed_intervals"])
        directory = evaluate(args.dataset, args.artifact_root, request_ids=tuple(args.request_id or ()),
                             subset=args.subset, all_samples=args.all_samples,
                             policy=ForecastPolicy(**config), run_id=args.run_id,
                             extraction_mode=args.extraction_mode)
    except (ValueError, TypeError, OSError) as exc:
        parser.exit(2, f"Evaluation setup failed: {exc}\n")
    metrics = json.loads((directory / "metrics.json").read_text())
    print(f"Selected {metrics['selected_requests']}; processed {metrics['successfully_processed']}; "
          f"unsupported {metrics['unsupported_requests']}; failed {metrics['failed_requests']}")
    print(f"Fully matching structured rows: {metrics['fully_matching_structured_rows']}/{metrics['selected_requests']}")
    for result in json.loads((directory / "request_results.json").read_text()):
        if result["processed"]:
            print(f"{result['request_id']}: processed; structured {result['structured_fields_correct']}/{result['structured_fields_total']}; "
                  f"explanation exact={result['explanation_exact_match']}; validation={result['validation']}")
        else:
            print(f"{result['request_id']}: {result['outcome']}; stage={result['failure_stage']}; {result['diagnostic']}")
    print(f"Artifacts: {directory.resolve()}")


if __name__ == "__main__":
    main()
