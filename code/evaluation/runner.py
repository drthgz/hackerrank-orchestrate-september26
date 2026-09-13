"""Per-request evaluation orchestration; financial behavior stays in the pipeline."""

import csv
import hashlib
import json
import re
import subprocess
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from buy_or_wait.domain import OUTPUT_COLUMNS, UnsupportedCase
from buy_or_wait.forecast import ForecastPolicy
from buy_or_wait.pipeline import run as run_pipeline
from .comparison import STRUCTURED_FIELDS, compare_prediction
from .samples import load_samples, select_samples, write_input
from .usage import UsageLedger

MISMATCH_COLUMNS = ("request_id", "field", "expected", "actual", "details", "failure_stage", "diagnostic", "policy_version", "kind")


def _json(value) -> str:
    return json.dumps(value, indent=2, sort_keys=True, default=lambda v: format(v, "f") if isinstance(v, Decimal) else str(v)) + "\n"


def _fingerprint(paths: list[Path], root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(str(path.relative_to(root)).encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _ratio(numerator: int, denominator: int) -> str | None:
    return format(Decimal(numerator) / denominator, "f") if denominator else None


def metrics_for(results: list[dict], mismatches: list[dict]) -> dict:
    successes = [r for r in results if r["outcome"] == "processed"]
    selected, processed = len(results), len(successes)
    fields = {}
    for field in STRUCTURED_FIELDS:
        matches = sum(next(c["match"] for c in r["comparisons"] if c["field"] == field) for r in successes)
        fields[field] = {"matches": matches, "selected": selected, "predictions": processed,
                         "accuracy_all_selected": _ratio(matches, selected),
                         "accuracy_processed_only": _ratio(matches, processed)}
    fully_matching = sum(r["structured_fields_correct"] == len(STRUCTURED_FIELDS) for r in successes)
    return {
        "selected_requests": selected, "successfully_processed": processed,
        "unsupported_requests": sum(r["outcome"] == "unsupported" for r in results),
        "failed_requests": sum(r["outcome"] == "failed" for r in results),
        "unsupported_or_failed": selected - processed,
        "structured_fields": list(STRUCTURED_FIELDS), "field_metrics": fields,
        "fully_matching_structured_rows": fully_matching,
        "fully_matching_fraction_all_selected": _ratio(fully_matching, selected),
        "fully_matching_fraction_processed_only": _ratio(fully_matching, processed),
        "total_mismatch_count": len(mismatches),
        "structured_mismatch_count": sum(m["field"] in STRUCTURED_FIELDS for m in mismatches),
        "missing_prediction_field_count": sum(m["kind"] == "missing_prediction" for m in mismatches),
        "comparable_structured_mismatch_count": sum(m["kind"] == "structured" for m in mismatches),
        "explanation_exact_matches": sum(r["explanation_exact_match"] is True for r in successes),
        "explanation_diagnostic_mismatches": sum(m["kind"] == "explanation" for m in mismatches),
        "failure_counts_by_stage": dict(Counter(r["failure_stage"] for r in results if r["outcome"] != "processed")),
        "mismatch_counts_by_field": dict(Counter(m["field"] for m in mismatches)),
        "notes": ["Internal development metrics, not an official HackerRank score.",
                  "Primary accuracy covers six financial fields; request_id and prose equality are diagnostics.",
                  "Missing predictions count as unmatched for all-selected accuracy, not as fabricated financial predictions.",
                  "Total mismatch count includes missing financial fields and diagnostic explanation/identifier differences.",
                  "Ratios are decimal strings between 0 and 1; null means no denominator."]}


def evaluate(dataset: Path, artifact_root: Path, *, request_ids: tuple[str, ...] = (),
             subset: str | None = None, all_samples: bool = False,
             policy: ForecastPolicy = ForecastPolicy(), run_id: str | None = None,
             extraction_mode: str = "disabled") -> Path:
    # Future live/cached implementations can supply the same pipeline interface.
    # Do not pretend those modes exist or fabricate cache activity today.
    if extraction_mode != "disabled":
        raise ValueError("Extraction is not implemented; only disabled mode is currently supported")
    selected = select_samples(load_samples(dataset / "sample_requests.csv"), request_ids, subset, all_samples)
    if not selected:
        raise ValueError("Empty evaluation selection")
    if artifact_root.resolve().is_relative_to(dataset.resolve()):
        raise ValueError("Evaluation artifacts cannot modify dataset files")
    timestamp = datetime.now(timezone.utc)
    run_id = run_id or timestamp.strftime("%Y%m%dT%H%M%S%fZ") + "-" + uuid4().hex[:8]
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", run_id):
        raise ValueError("Run ID must be a simple directory name")
    directory = artifact_root / run_id
    directory.mkdir(parents=True, exist_ok=False)
    results, mismatches, predicted_rows = [], [], []
    usage = UsageLedger()  # No model calls or extraction in the current pipeline.
    for index, sample in enumerate(selected):
        rid = sample.inputs["request_id"]
        request_dir = directory / "requests" / f"{index:04d}"
        input_path, output_path = request_dir / "input.csv", request_dir / "prediction.csv"
        result = {"request_id": rid, "outcome": None, "processed": False,
                  "failure_stage": None, "diagnostic": None, "error_type": None,
                  "policy_version": policy.version, "validation": "not_reached",
                  "structured_fields_correct": None, "structured_fields_total": len(STRUCTURED_FIELDS),
                  "explanation_exact_match": None, "explanation_consistency": "not_assessed",
                  "comparisons": []}
        stage = "loading"
        try:
            write_input(input_path, sample.inputs)
            stage = "unknown"
            # The only application arguments are input-only paths and policy.
            # Never pass Sample or expected answers to application code.
            run_pipeline(input_path, dataset, output_path, policy)
            stage = "serialization"
            with output_path.open(encoding="utf-8", newline="") as stream:
                reader = csv.DictReader(stream)
                if tuple(reader.fieldnames or ()) != OUTPUT_COLUMNS:
                    raise ValueError("Unexpected serialized prediction schema")
                rows = list(reader)
            if len(rows) != 1:
                raise ValueError("Expected one serialized prediction per request")
            stage = "comparison"
            comparisons = compare_prediction(sample.expected, rows[0])
            result.update(outcome="processed", processed=True, validation="passed", comparisons=comparisons,
                          structured_fields_correct=sum(c["match"] for c in comparisons if c["field"] in STRUCTURED_FIELDS),
                          explanation_exact_match=next(c["match"] for c in comparisons if c["field"] == "decision_explanation"))
            predicted_rows.append(rows[0])
            for comparison in comparisons:
                if comparison["match"]:
                    continue
                field = comparison["field"]
                mismatches.append({"request_id": rid, "field": field, "expected": comparison["expected"],
                                   "actual": comparison["actual"], "details": json.dumps(comparison["details"], sort_keys=True),
                                   "failure_stage": "unknown" if field in STRUCTURED_FIELDS else "comparison",
                                   "diagnostic": "Field mismatch does not establish a causal pipeline stage.",
                                   "policy_version": policy.version,
                                   "kind": "structured" if field in STRUCTURED_FIELDS else "explanation" if field == "decision_explanation" else "identifier"})
        except Exception as exc:
            failure_stage = getattr(exc, "failure_stage", stage)
            outcome = "unsupported" if isinstance(exc, UnsupportedCase) else "failed"
            result.update(outcome=outcome, failure_stage=failure_stage, diagnostic=str(exc), error_type=type(exc).__name__,
                          validation="failed" if failure_stage == "validation" else "not_reached")
            for field in STRUCTURED_FIELDS:
                mismatches.append({"request_id": rid, "field": field, "expected": sample.expected[field], "actual": "",
                                   "details": json.dumps({"reason": "no_prediction", "absolute_error": None}),
                                   "failure_stage": failure_stage, "diagnostic": str(exc), "policy_version": policy.version,
                                   "kind": "missing_prediction"})
        results.append(result)
    with (directory / "predictions.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=OUTPUT_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(predicted_rows)
    with (directory / "mismatches.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=MISMATCH_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(mismatches)
    (directory / "metrics.json").write_text(_json(metrics_for(results, mismatches)), encoding="utf-8")
    (directory / "request_results.json").write_text(_json(results), encoding="utf-8")
    (directory / "usage.json").write_text(_json(usage.to_dict()), encoding="utf-8")
    root = dataset.resolve().parent
    try:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True, stderr=subprocess.DEVNULL).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        commit = None
    configuration = asdict(policy)
    metadata = {"run_id": run_id, "timestamp_utc": timestamp.isoformat(),
                "selection": {"mode": "all" if all_samples else "subset" if subset else "explicit", "subset": subset,
                              "request_ids": [s.inputs["request_id"] for s in selected]},
                "number_of_requests": len(selected), "forecast_policy_version": policy.version,
                "forecast_policy": configuration, "config_sha256": hashlib.sha256(_json(configuration).encode()).hexdigest(),
                "git_commit": commit,
                "source_sha256": _fingerprint(list((root / "code").rglob("*.py")) + list((root / "scripts").glob("*.py")), root),
                "dataset_sha256": _fingerprint(list(dataset.rglob("*.csv")) + list(dataset.rglob("*.png")), dataset),
                "extraction_mode": extraction_mode, "extraction_implemented": False,
                "application_input_boundary": "requests/*/input.csv contains exactly request input columns; answers are evaluator-only"}
    (directory / "metadata.json").write_text(_json(metadata), encoding="utf-8")
    return directory
