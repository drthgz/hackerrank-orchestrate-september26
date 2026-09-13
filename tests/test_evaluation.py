"""Evaluation tests do not tune the engine or embed sample answer conditions."""

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))

from buy_or_wait.domain import OUTPUT_COLUMNS, REQUEST_COLUMNS
from buy_or_wait.forecast import ForecastPolicy
from buy_or_wait.pipeline import run as actual_pipeline
from evaluation.comparison import STRUCTURED_FIELDS, compare_field, compare_prediction
from evaluation.runner import evaluate, metrics_for
from evaluation.samples import Sample, load_samples, select_samples
from evaluation.usage import UsageLedger


def example():
    return dict(zip(OUTPUT_COLUMNS, (
        "r", "10.00", "affordable_with_plan", "partial_payment",
        "2026-01-01:10.00|2026-01-15:20.0", "2026-01-15", "none", "Example explanation",
    )))


class ComparisonTest(unittest.TestCase):
    def test_exact_structured_match(self):
        self.assertTrue(all(c["match"] for c in compare_prediction(example(), example())))

    def test_money_is_semantic_and_error_is_decimal(self):
        self.assertTrue(compare_field("amount_safe_to_pay", "10.00", "10")["match"])
        result = compare_field("amount_safe_to_pay", "0.1", "0.3")
        self.assertFalse(result["match"])
        self.assertEqual(result["details"]["absolute_error"], "0.2")

    def test_dates_report_signed_difference_and_missing_date(self):
        result = compare_field("earliest_date_for_full_payment", "2026-07-18", "2026-07-22")
        self.assertEqual(result["details"]["day_difference_actual_minus_expected"], 4)
        result = compare_field("earliest_date_for_full_payment", "", "2026-07-22")
        self.assertIsNone(result["details"]["day_difference_actual_minus_expected"])
        self.assertTrue(result["details"]["presence_mismatch"])

    def test_payment_plan_semantics(self):
        self.assertTrue(compare_field("payment_plan", "2026-01-01:10.00|2026-01-15:20.0", "2026-01-01:10|2026-01-15:20")["match"])
        self.assertFalse(compare_field("payment_plan", "2026-01-01:10|2026-01-01:20", "2026-01-01:30")["match"])
        mismatch = compare_field("payment_plan", "2026-01-01:10", "2026-01-02:10")
        self.assertEqual(mismatch["details"]["different_payment_indexes"], [0])

    def test_spending_changes_are_order_independent(self):
        self.assertTrue(compare_field("spending_changes_needed", "stop:e1|reduce_to:e2:10.00", "reduce_to:e2:10|stop:e1")["match"])
        self.assertFalse(compare_field("spending_changes_needed", "none", "stop:e1|reduce_to:e1:10")["match"])

    def test_invalid_numeric_and_dates_are_diagnostics(self):
        for field, expected, actual in (("amount_safe_to_pay", "1", "NaN"), ("earliest_date_for_full_payment", "2026-01-01", "20260101")):
            result = compare_field(field, expected, actual)
            self.assertFalse(result["match"])
            self.assertIn("comparison_error", result["details"])

    def test_metrics_exclude_prose_and_expose_missing_predictions(self):
        actual = dict(example(), decision_explanation="Different valid wording")
        comparisons = compare_prediction(example(), actual)
        results = [dict(outcome="processed", comparisons=comparisons, structured_fields_correct=6, explanation_exact_match=False, failure_stage=None),
                   dict(outcome="unsupported", failure_stage="forecast")]
        mismatches = [{"field": field, "kind": "missing_prediction"} for field in STRUCTURED_FIELDS]
        mismatches.append({"field": "decision_explanation", "kind": "explanation"})
        metrics = metrics_for(results, mismatches)
        self.assertEqual(metrics["fully_matching_structured_rows"], 1)
        self.assertEqual(metrics["total_mismatch_count"], 7)
        self.assertEqual(metrics["structured_mismatch_count"], 6)
        self.assertEqual(metrics["field_metrics"]["amount_safe_to_pay"]["accuracy_all_selected"], "0.5")
        self.assertEqual(metrics["field_metrics"]["amount_safe_to_pay"]["accuracy_processed_only"], "1")

    def test_zero_processed_denominator_is_null(self):
        metrics = metrics_for([dict(outcome="unsupported", failure_stage="forecast")], [])
        self.assertIsNone(metrics["field_metrics"]["amount_safe_to_pay"]["accuracy_processed_only"])
        self.assertEqual(metrics["field_metrics"]["amount_safe_to_pay"]["accuracy_all_selected"], "0")


class EvaluationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.artifacts = Path(self.temp.name)
        self.dataset = ROOT / "dataset"
        self.samples = load_samples(self.dataset / "sample_requests.csv")

    def test_single_multiple_smoke_and_all_selection(self):
        one = select_samples(self.samples, ("request_09",))
        self.assertEqual([s.inputs["request_id"] for s in one], ["request_09"])
        multiple = select_samples(self.samples, ("request_01", "request_09"))
        self.assertEqual([s.inputs["request_id"] for s in multiple], ["request_01", "request_09"])
        self.assertEqual(len(select_samples(self.samples, subset="smoke")), 2)
        self.assertEqual(len(select_samples(self.samples, all_samples=True)), 25)
        for ids in (("missing",), ("request_09", "request_09")):
            with self.assertRaises(ValueError):
                select_samples(self.samples, ids)

    def test_answers_cannot_reach_pipeline_and_do_not_change_prediction(self):
        selected = select_samples(self.samples, ("request_09",))[0]
        reference = evaluate(self.dataset, self.artifacts, request_ids=("request_09",), run_id="reference")
        altered = Sample(dict(selected.inputs), {key: selected.expected[key] if key == "request_id" else "ANSWER_SENTINEL" for key in OUTPUT_COLUMNS})
        observed = []

        def spy(input_path, dataset, output, policy):
            with input_path.open() as stream:
                reader = csv.DictReader(stream)
                self.assertEqual(tuple(reader.fieldnames), REQUEST_COLUMNS)
                row = next(reader)
            self.assertNotIn("ANSWER_SENTINEL", input_path.read_text())
            self.assertEqual(row, selected.inputs)
            observed.append(True)
            return actual_pipeline(input_path, dataset, output, policy)

        with patch("evaluation.runner.load_samples", return_value=(altered,)), patch("evaluation.runner.run_pipeline", side_effect=spy):
            changed = evaluate(self.dataset, self.artifacts, request_ids=("request_09",), run_id="changed")
        self.assertEqual(observed, [True])
        self.assertEqual((reference / "predictions.csv").read_bytes(), (changed / "predictions.csv").read_bytes())

    def test_smoke_continues_after_unsupported_and_writes_artifacts(self):
        directory = evaluate(self.dataset, self.artifacts, request_ids=("request_01", "request_09"), run_id="smoke")
        metrics = json.loads((directory / "metrics.json").read_text())
        results = json.loads((directory / "request_results.json").read_text())
        self.assertEqual(metrics["selected_requests"], 2)
        self.assertEqual(metrics["successfully_processed"], 2)
        self.assertEqual(metrics["unsupported_requests"], 0)
        self.assertIsNone(results[0]["failure_stage"])
        self.assertEqual(results[1]["validation"], "passed")
        with (directory / "mismatches.csv").open() as stream:
            mismatches = list(csv.DictReader(stream))
        missing = [m for m in mismatches if m["kind"] == "missing_prediction"]
        self.assertEqual(missing, [])
        self.assertTrue((directory / "metadata.json").is_file())

    def test_zero_usage_is_truthful(self):
        self.assertEqual(UsageLedger().to_dict()["records"], [])
        directory = evaluate(self.dataset, self.artifacts, request_ids=("request_09",), run_id="zero")
        usage = json.loads((directory / "usage.json").read_text())
        self.assertEqual(usage["totals"]["model_calls"], 0)
        self.assertEqual(usage["totals"]["total_tokens"], 0)
        self.assertEqual(usage["totals"]["cache_hits"], 0)
        self.assertEqual(usage["totals"]["cache_misses"], 0)
        self.assertEqual(usage["totals"]["estimated_cost"], "0")

    def test_numeric_mismatch_is_written_with_exact_error(self):
        selected = select_samples(self.samples, ("request_09",))[0]
        from decimal import Decimal
        expected = dict(selected.expected)
        expected["amount_safe_to_pay"] = str(Decimal(selected.inputs["requested_amount"]) + Decimal("0.10"))
        with patch("evaluation.runner.load_samples", return_value=(Sample(selected.inputs, expected),)):
            directory = evaluate(self.dataset, self.artifacts, request_ids=("request_09",), run_id="numeric")
        with (directory / "mismatches.csv").open() as stream:
            row = next(r for r in csv.DictReader(stream) if r["field"] == "amount_safe_to_pay")
        self.assertEqual(json.loads(row["details"])["absolute_error"], "0.10")
        self.assertEqual(row["kind"], "structured")
        metrics = json.loads((directory / "metrics.json").read_text())
        self.assertEqual(metrics["comparable_structured_mismatch_count"], 1)

    def test_unknown_exception_is_not_misclassified_as_forecast(self):
        with patch("evaluation.runner.run_pipeline", side_effect=RuntimeError("Unexpected test failure")):
            directory = evaluate(self.dataset, self.artifacts, request_ids=("request_09",), run_id="unknown")
        result = json.loads((directory / "request_results.json").read_text())[0]
        self.assertEqual(result["outcome"], "failed")
        self.assertEqual(result["failure_stage"], "unknown")

    def test_actual_serialization_and_validation_stages_are_preserved(self):
        for operation, stage in (("write_predictions", "serialization"), ("validate_output", "validation")):
            with patch("buy_or_wait.pipeline." + operation, side_effect=ValueError("Injected boundary failure")):
                directory = evaluate(self.dataset, self.artifacts, request_ids=("request_09",), run_id=stage)
            result = json.loads((directory / "request_results.json").read_text())[0]
            self.assertEqual(result["failure_stage"], stage)
            self.assertEqual(result["outcome"], "failed")

    def test_runs_are_immutable_and_configs_have_identifiers(self):
        first = evaluate(self.dataset, self.artifacts, request_ids=("request_09",), run_id="first")
        second = evaluate(self.dataset, self.artifacts, request_ids=("request_09",), run_id="second", policy=ForecastPolicy(version="configuration-test"))
        a, b = [json.loads((d / "metadata.json").read_text()) for d in (first, second)]
        self.assertNotEqual(a["config_sha256"], b["config_sha256"])
        self.assertEqual(a["source_sha256"], b["source_sha256"])
        with self.assertRaises(FileExistsError):
            evaluate(self.dataset, self.artifacts, request_ids=("request_09",), run_id="first")

    def test_live_extraction_not_silently_simulated(self):
        with self.assertRaisesRegex(ValueError, "not implemented"):
            evaluate(self.dataset, self.artifacts, request_ids=("request_09",), extraction_mode="live")


if __name__ == "__main__":
    unittest.main()
