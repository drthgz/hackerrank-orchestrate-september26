"""Focused contracts and boundary tests; no benchmark evaluator."""

import csv
import sys
import tempfile
import unittest
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))
sys.path.insert(0, str(ROOT / "scripts"))

from buy_or_wait.domain import (DataError, Method, OUTPUT_COLUMNS, Payment,
                               Prediction, REQUEST_COLUMNS, Status)
from buy_or_wait.loading import SCHEMAS, build_context, load_requests
from buy_or_wait.normalize import normalize
from buy_or_wait.output import prediction_row, write_predictions
from buy_or_wait.validation import ValidationError, validate_output, validate_row
from sample_inputs import INPUT_COLUMNS, prepare_inputs


def write_csv(path, columns, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


class ContractsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.request = dict(zip(REQUEST_COLUMNS, (
            "r", "u", "2026-01-03", "purchase", "10.25", "2026-01-20", "true", "A purchase",
        )))
        self.profile = dict(zip(SCHEMAS["financial_profiles"], (
            "u", "EUR", "1000.10", "100", "savings", "rent", "", "", "full_payment", "",
        )))
        self.event = dict(zip(SCHEMAS["financial_events"], (
            "e", "u", "expense", "Rent", "rent", "debit", "100.01", "EUR",
            "2026-01-02", "2026-01-02", "settled", "", "fixed", "",
        )))
        self.options = [dict(zip(SCHEMAS["request_payment_options"], values)) for values in (
            ("o1", "r", "full_payment", "10.25", "1", "2026-01-03", "", "0", "10.25"),
            ("o2", "r", "installments", "5.25", "2", "2026-01-03", "28", "0.25", "10.50"),
        )]
        self.tables = {name: [] for name in SCHEMAS}
        self.tables.update(financial_profiles=[self.profile], financial_events=[self.event], request_payment_options=self.options)
        self.save_tables()

    def save_tables(self):
        for name, columns in SCHEMAS.items():
            write_csv(self.root / f"{name}.csv", columns, self.tables[name])

    def context(self):
        return normalize(build_context(self.root, self.request))

    def prediction(self):
        return Prediction("r", Decimal("10.25"), Status.NOW, Method.FULL,
                          (Payment(date(2026, 1, 3), Decimal("10.25")),),
                          date(2026, 1, 3), (), 'Pay EUR 10.25; quoted "item".')

    def test_request_schema_and_context_joins(self):
        path = self.root / "inputs.csv"
        write_csv(path, REQUEST_COLUMNS, [self.request])
        loaded = load_requests(path)
        self.assertEqual(loaded, (self.request,))
        context = build_context(self.root, loaded[0])
        self.assertEqual(context.profile["user_id"], "u")
        self.assertEqual(len(context.events), 1)
        self.assertEqual(len(context.options), 2)

    def test_application_rejects_answer_columns(self):
        combined = dict(self.request, amount_safe_to_pay="999")
        path = self.root / "combined.csv"
        write_csv(path, tuple(combined), [combined])
        with self.assertRaises(DataError):
            load_requests(path)
        with self.assertRaises(DataError):
            build_context(self.root, combined)

    def test_answer_changes_cannot_affect_projected_inputs(self):
        self.assertEqual(INPUT_COLUMNS, REQUEST_COLUMNS)
        path = self.root / "samples.csv"
        projected = self.root / "projected.csv"
        columns = REQUEST_COLUMNS + OUTPUT_COLUMNS[1:]
        row = dict(self.request, **{key: "ANSWER_SENTINEL" for key in OUTPUT_COLUMNS[1:]})
        write_csv(path, columns, [row])
        prepare_inputs(path, projected, ("r",))
        first = projected.read_bytes()
        row.update({key: "DIFFERENT_ANSWER" for key in OUTPUT_COLUMNS[1:]})
        write_csv(path, columns, [row])
        prepare_inputs(path, projected, ("r",))
        self.assertEqual(first, projected.read_bytes())
        self.assertNotIn(b"ANSWER", first)
        self.assertEqual(load_requests(projected), (self.request,))

    def test_duplicate_and_dangling_references_fail(self):
        for changed in (dict(self.event, linked_event_id="missing"), dict(self.event, user_id="missing")):
            with self.subTest(changed=changed):
                self.tables["financial_events"] = [changed]
                self.save_tables()
                with self.assertRaises(DataError):
                    build_context(self.root, self.request)
        self.tables["financial_events"] = [self.event, self.event]
        self.save_tables()
        with self.assertRaises(DataError):
            build_context(self.root, self.request)

    def test_conflicting_evidence_reference_fails(self):
        self.tables["messages"] = [dict(zip(SCHEMAS["messages"], (
            "m", "u", "other_request", "e", "2026-01-01T00:00:00Z", "bank", "Evidence",
        )))]
        self.save_tables()
        with self.assertRaises(DataError):
            build_context(self.root, self.request)

    def test_normalized_decimals_dates_and_provenance(self):
        context = self.context()
        self.assertEqual(context.request.requested_amount, Decimal("10.25"))
        self.assertEqual(context.profile.balance, Decimal("1000.10"))
        self.assertEqual(context.events[0].source.source_id, "e")
        self.assertEqual(context.events[0].settlement_date, date(2026, 1, 2))

    def test_missing_amount_is_unresolved_not_zero(self):
        self.event["amount"] = ""
        self.save_tables()
        self.assertIsNone(self.context().events[0].amount)

    def test_missing_fx_is_an_error(self):
        self.event["currency"] = "USD"
        self.save_tables()
        with self.assertRaises(DataError):
            self.context()
        self.tables["exchange_rates"] = [dict(rate_date="2026-01-02", from_currency="USD", to_currency="EUR", rate="0.9")]
        self.save_tables()
        self.assertEqual(self.context().rates[0].rate, Decimal("0.9"))

    def test_malformed_money_date_and_schedule_fail(self):
        for column, value in (("amount", "NaN"), ("amount", "1e3"), ("amount", "-1"), ("settlement_date", "20260102")):
            with self.subTest(column=column, value=value):
                raw = build_context(self.root, self.request)
                altered = dict(raw.events[0], **{column: value})
                with self.assertRaises(DataError):
                    normalize(replace(raw, events=(altered,)))
        self.options[1]["total_payable_amount"] = "10.51"
        self.save_tables()
        with self.assertRaises(DataError):
            self.context()

    def test_csv_round_trip_and_repeatability(self):
        path = self.root / "prediction.csv"
        write_predictions(path, (self.prediction(),))
        before = path.read_bytes()
        validate_output(path, (self.context().request,))
        with path.open(newline="") as stream:
            row = next(csv.DictReader(stream))
        self.assertEqual(tuple(row), OUTPUT_COLUMNS)
        self.assertEqual(row["decision_explanation"], self.prediction().decision_explanation)
        write_predictions(path, (self.prediction(),))
        self.assertEqual(path.read_bytes(), before)

    def test_validator_rejects_invalid_outputs(self):
        alterations = (
            {"affordability_status": "maybe"},
            {"recommended_payment_method": "cash"},
            {"amount_safe_to_pay": "100"},
            {"amount_safe_to_pay": "NaN"},
            {"amount_safe_to_pay": "1e1"},
            {"earliest_date_for_full_payment": "20260103"},
            {"payment_plan": "none"},
            {"payment_plan": "2026-01-21:10.25"},
            {"payment_plan": "2026-01-03:0"},
            {"payment_plan": "2026-01-03:10"},
            {"decision_explanation": ""},
            {"spending_changes_needed": "stop:e|reduce_to:e:10"},
        )
        for alteration in alterations:
            with self.subTest(alteration=alteration):
                row = prediction_row(self.prediction())
                row.update(alteration)
                with self.assertRaises(ValidationError):
                    validate_row(row, self.context().request)

    def test_validator_checks_header_duplicates_and_coverage(self):
        path = self.root / "prediction.csv"
        row = prediction_row(self.prediction())
        for columns, rows in ((OUTPUT_COLUMNS[::-1], [row]), (OUTPUT_COLUMNS, [row, row]), (OUTPUT_COLUMNS, [])):
            with self.subTest(columns=columns, rows=len(rows)):
                write_csv(path, columns, rows)
                with self.assertRaises(ValidationError):
                    validate_output(path, (self.context().request,))

    def test_partial_plan_contract(self):
        row = prediction_row(replace(self.prediction(), amount_safe_to_pay=Decimal("4"), affordability_status=Status.PLAN, recommended_payment_method=Method.PARTIAL, payment_plan=(Payment(date(2026, 1, 3), Decimal("4")), Payment(date(2026, 1, 15), Decimal("6.25"))), earliest_date_for_full_payment=date(2026, 1, 15)))
        validate_row(row, self.context().request)
        row["payment_plan"] = "2026-01-03:4|2026-01-14:6.25"
        with self.assertRaises(ValidationError):
            validate_row(row, self.context().request)

    def test_selected_sample_inputs_reach_normalized_boundary(self):
        projected = self.root / "sample_inputs.csv"
        prepare_inputs(ROOT / "dataset" / "sample_requests.csv", projected, ("request_01", "request_09"))
        contexts = tuple(normalize(build_context(ROOT / "dataset", row)) for row in load_requests(projected))
        self.assertEqual([c.request.request_id for c in contexts], ["request_01", "request_09"])
        self.assertTrue(all(not c.evidence for c in contexts))
        self.assertTrue(all(e.amount is not None for c in contexts for e in c.events))
        self.assertTrue(all(e.currency == c.profile.currency for c in contexts for e in c.events))


if __name__ == "__main__":
    unittest.main()
