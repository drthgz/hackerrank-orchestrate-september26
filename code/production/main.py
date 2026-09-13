"""Diagnostic production runner; writes artifacts only, never the root output.csv."""

import argparse
import csv
import json
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from buy_or_wait.domain import OUTPUT_COLUMNS, UnsupportedCase
from buy_or_wait.extraction import ExtractionConfig
from buy_or_wait.forecast import ForecastPolicy
from buy_or_wait.loading import load_requests
from buy_or_wait.pipeline import run
from buy_or_wait.validation import validate_output
from evaluation.samples import write_input
from evaluation.usage import ModelUsage, UsageLedger


def _json(value) -> str:
    return json.dumps(value, indent=2, sort_keys=True,
                      default=lambda item: format(item, "f") if isinstance(item, Decimal) else str(item)) + "\n"


def execute(dataset: Path, directory: Path, extraction_mode: str) -> Path:
    if directory.exists():
        raise ValueError(f"Production artifact directory already exists: {directory}")
    if directory.resolve().is_relative_to(dataset.resolve()):
        raise ValueError("Production artifacts cannot be written inside dataset")
    directory.mkdir(parents=True)
    requests = load_requests(dataset / "requests.csv")
    results, output_rows = [], []
    usage = UsageLedger()
    policy = ForecastPolicy()
    cache = directory.parent.parent / "extraction-cache"
    for index, request in enumerate(requests):
        request_dir = directory / "requests" / f"{index:04d}"
        input_path = request_dir / "input.csv"
        output_path = request_dir / "prediction.csv"
        measured = []
        result = {"request_id": request["request_id"], "outcome": None,
                  "failure_stage": None, "diagnostic": None, "error_type": None}
        try:
            write_input(input_path, request)
            run(input_path, dataset, output_path, policy,
                ExtractionConfig(mode=extraction_mode, cache_dir=cache), measured)
            with output_path.open(encoding="utf-8", newline="") as stream:
                rows = list(csv.DictReader(stream))
            if len(rows) != 1 or tuple(rows[0]) != OUTPUT_COLUMNS:
                raise ValueError("Per-request output has unexpected shape")
            output_rows.append(rows[0])
            result["outcome"] = "processed"
        except Exception as exc:
            result.update(outcome="unsupported" if isinstance(exc, UnsupportedCase) else "failed",
                          failure_stage=getattr(exc, "failure_stage", "unknown"),
                          diagnostic=str(exc), error_type=type(exc).__name__)
        finally:
            for item in measured:
                usage.record(ModelUsage(item.provider, item.model, item.model_calls,
                                        item.input_tokens, item.output_tokens, item.retries,
                                        item.cache_hits, item.cache_misses, item.estimated_cost))
        results.append(result)
    output = directory / "output.csv"
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=OUTPUT_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(output_rows)
    validation = {"passed": False, "diagnostic": None}
    try:
        # The validator reopens and parses the serialized artifact.
        from buy_or_wait.domain import Request
        from buy_or_wait.normalize import day, money
        typed_requests = tuple(Request(
            request["request_id"], request["user_id"], day(request["request_date"]),
            request["request_type"], money(request["requested_amount"]),
            day(request["desired_completion_date"]),
            request["allows_partial_payment"] == "true", request["request_text"])
            for request in requests)
        validate_output(output, typed_requests)
        validation["passed"] = True
    except Exception as exc:
        validation["diagnostic"] = str(exc)
    summary = {
        "total_requests": len(requests),
        "successful_requests": sum(r["outcome"] == "processed" for r in results),
        "unsupported_requests": sum(r["outcome"] == "unsupported" for r in results),
        "failed_requests": sum(r["outcome"] == "failed" for r in results),
        "failure_counts_by_stage": dict(Counter(r["failure_stage"] for r in results if r["outcome"] != "processed")),
        "output_rows": len(output_rows), "read_back_validation": validation,
    }
    (directory / "request_results.json").write_text(_json(results), encoding="utf-8")
    (directory / "usage.json").write_text(_json(usage.to_dict()), encoding="utf-8")
    (directory / "summary.json").write_text(_json(summary), encoding="utf-8")
    (directory / "metadata.json").write_text(_json({
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "forecast_policy": asdict(policy), "extraction_mode": extraction_mode,
        "dataset": str(dataset.resolve()),
    }), encoding="utf-8")
    return directory


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=root / "dataset")
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--extraction-mode", choices=("live", "cached", "deterministic-only"), default="live")
    args = parser.parse_args()
    try:
        directory = execute(args.dataset, args.artifact_dir, args.extraction_mode)
    except (OSError, ValueError) as exc:
        parser.exit(2, f"Production run setup failed: {exc}\n")
    print((directory / "summary.json").read_text(), end="")
    print(f"Artifacts: {directory.resolve()}")


if __name__ == "__main__":
    main()
