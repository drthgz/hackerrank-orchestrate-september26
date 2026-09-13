"""Provisional policy tests with independent synthetic cash-flow expectations."""

import sys
import tempfile
import unittest
from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))
sys.path.insert(0, str(ROOT / "scripts"))

from buy_or_wait.domain import (Event, FinancialContext, Method, Payment,
                               PaymentOption, Profile, Request, Source, UnsupportedCase)
from buy_or_wait.forecast import (ForecastEntry, ForecastPolicy, ForecastTimeline,
                                 build_forecast, infer_occurrences, simulate)
from buy_or_wait.pipeline import run
from buy_or_wait.processing import decide
from buy_or_wait.validation import validate_output
from sample_inputs import prepare_inputs


def event(identifier, when, amount="10", direction="debit", status="settled", linked=None):
    return Event(identifier, "rent" if direction == "debit" else "salary",
                 "expense" if direction == "debit" else "income", "Structured stream",
                 Decimal(amount), "EUR", direction, when, when, status, linked,
                 "fixed", None, Source("financial_event", identifier))


def context(events):
    request = Request("synthetic", "u", date(2026, 4, 3), "purchase", Decimal("10"), date(2026, 4, 20), False, "Purchase")
    profile = Profile("u", "EUR", Decimal("100"), Decimal("10"), frozenset({Method.FULL}), frozenset({"rent"}), frozenset(), frozenset(), None)
    option = PaymentOption("option", Method.FULL, Decimal("10"), 1, request.request_date, None, Decimal("0"), Decimal("10"))
    return FinancialContext(request, profile, tuple(events), (option,), (), ())


class ForecastTest(unittest.TestCase):
    def history(self, direction="debit"):
        return tuple(event(f"e{i}", date(2026, i, 6), direction=direction) for i in (1, 2, 3))

    def test_clear_monthly_recurrence(self):
        timeline = build_forecast(context(self.history()))
        self.assertEqual([(e.date, e.amount) for e in timeline.entries], [(date(2026, m, 6), Decimal("-10")) for m in (4, 5, 6)])
        self.assertEqual(timeline.end, date(2026, 7, 2))

    def test_single_occurrence_is_unresolved(self):
        # A singleton is classified as one-time and never projected.
        self.assertEqual(build_forecast(context(self.history()[:1])).entries, ())

    def test_ambiguous_cadence_is_unresolved(self):
        events = self.history()[:2] + (event("last", date(2026, 3, 9)),)
        with self.assertRaisesRegex(UnsupportedCase, "cadence"):
            build_forecast(context(events))

    def test_variable_amounts_use_conservative_extremes(self):
        for direction, expected in (("debit", Decimal("-11")), ("credit", Decimal("9"))):
            history = tuple(replace(e, amount=Decimal(a)) for e, a in zip(self.history(direction), ("9", "10", "11")))
            self.assertTrue(all(e.amount == expected for e in build_forecast(context(history)).entries))
        history = self.history()[:2] + (replace(self.history()[2], amount=Decimal("100")),)
        self.assertTrue(all(e.amount == Decimal("-100") for e in build_forecast(context(history)).entries))

    def test_explicit_future_replaces_inferred_occurrence(self):
        explicit = event("future", date(2026, 4, 6), "12", status="scheduled")
        timeline = build_forecast(context(self.history() + (explicit,)))
        april = [e for e in timeline.entries if e.date == explicit.settlement_date]
        self.assertEqual(len(april), 1)
        self.assertEqual(april[0].amount, Decimal("-12"))
        self.assertEqual(april[0].basis, "explicit")

    def test_pending_credit_suppresses_inference_without_adding_cash(self):
        # Regression: dropping the pending row before deduplication would recreate
        # its credit through recurrence and incorrectly increase available cash.
        pending = event("pending", date(2026, 4, 6), direction="credit", status="pending")
        timeline = build_forecast(context(self.history("credit") + (pending,)))
        self.assertFalse(any(e.date == pending.settlement_date for e in timeline.entries))
        self.assertEqual(sum(e.amount for e in timeline.entries), Decimal("20"))

    def test_pending_debit_reserved_today_once(self):
        pending = event("pending", date(2026, 4, 6), status="pending")
        timeline = build_forecast(context(self.history() + (pending,)))
        self.assertEqual(len(timeline.entries), 3)
        self.assertEqual(timeline.entries[0].date, timeline.start)
        self.assertEqual(sum(e.amount for e in timeline.entries), Decimal("-30"))

    def test_pending_to_settled_link_is_not_double_counted(self):
        pending = event("pending", date(2026, 4, 6), status="pending")
        settlement = event("settlement", date(2026, 4, 6), linked="pending")
        timeline = build_forecast(context(self.history() + (pending, settlement)))
        self.assertEqual(sum(e.amount for e in timeline.entries), Decimal("-30"))
        self.assertFalse(any(e.entry_id == "pending" for e in timeline.entries))
        self.assertEqual(next(e.date for e in timeline.entries if e.entry_id == "settlement"), timeline.start)

    def test_minimum_violation_and_equality(self):
        timeline = build_forecast(context(self.history()))
        equal = simulate(timeline, (Payment(timeline.start, Decimal("60")),))
        self.assertEqual(equal.minimum_balance, Decimal("10"))
        self.assertTrue(equal.safe)
        self.assertFalse(simulate(timeline, (Payment(timeline.start, Decimal("60.01")),)).safe)
        unsafe = replace(timeline, opening_balance=Decimal("40"))
        with self.assertRaisesRegex(UnsupportedCase, "unsafe"):
            decide(context(self.history()), unsafe)

    def test_decimal_arithmetic_and_same_day_order(self):
        start = date(2026, 4, 3)
        entries = (ForecastEntry(start, Decimal("1"), "credit", (), "explicit"), ForecastEntry(start, Decimal("-0.1"), "debit", (), "explicit"))
        timeline = ForecastTimeline(start, start + timedelta(days=90), Decimal("0.3"), Decimal("0"), entries, ForecastPolicy())
        result = simulate(timeline, (Payment(start, Decimal("0.2")),))
        self.assertEqual(result.minimum_balance, Decimal("0"))
        self.assertTrue(result.safe)
        self.assertEqual([p.entry_id for p in result.points], ["opening", "debit", "payment:0", "credit"])
        self.assertEqual(result, simulate(replace(timeline, entries=entries[::-1]), (Payment(start, Decimal("0.2")),)))
        self.assertFalse(simulate(timeline, (Payment(start, Decimal("0.21")),)).safe)

    def test_fixed_day_cadence(self):
        start = date(2026, 4, 3)
        events = tuple(event(str(i), start - timedelta(days=21 * i)) for i in (3, 2, 1))
        occurrences = infer_occurrences(events, start, start + timedelta(days=90), ForecastPolicy())
        self.assertEqual([when for when, _ in occurrences], [start + timedelta(days=21 * i) for i in range(5)])

    def test_missing_amount_and_mixed_directions_rejected(self):
        with self.assertRaisesRegex(UnsupportedCase, "Missing financial amount"):
            build_forecast(context((replace(self.history()[0], amount=None),)))
        with self.assertRaisesRegex(UnsupportedCase, "Mixed financial streams"):
            infer_occurrences(self.history()[:2] + (replace(self.history()[2], direction="credit"),), date(2026, 4, 3), date(2026, 7, 2), ForecastPolicy())

    def test_request_09_end_to_end_repeatable_without_labels(self):
        with tempfile.TemporaryDirectory() as temporary:
            inputs, output = Path(temporary) / "requests.csv", Path(temporary) / "predictions.csv"
            prepare_inputs(ROOT / "dataset" / "sample_requests.csv", inputs, ("request_09",))
            predictions = run(inputs, ROOT / "dataset", output)
            original = output.read_bytes()
            self.assertEqual(len(predictions), 1)
            self.assertEqual(predictions[0].request_id, "request_09")
            # No label assertions: check repeatability and input-derived cap.
            self.assertEqual(predictions[0].amount_safe_to_pay, predictions[0].payment_plan[0].amount)
            run(inputs, ROOT / "dataset", output)
            self.assertEqual(output.read_bytes(), original)

    def test_unsupported_sample_does_not_write_prediction(self):
        with tempfile.TemporaryDirectory() as temporary:
            inputs, output = Path(temporary) / "requests.csv", Path(temporary) / "predictions.csv"
            prepare_inputs(ROOT / "dataset" / "sample_requests.csv", inputs, ("request_01",))
            with self.assertRaises(UnsupportedCase):
                run(inputs, ROOT / "dataset", output)
            self.assertFalse(output.exists())

    def test_final_output_and_dataset_are_protected(self):
        for target in (ROOT / "output.csv", ROOT / "dataset" / "output.csv"):
            with self.assertRaisesRegex(ValueError, "cannot overwrite"):
                run(Path("unused.csv"), ROOT / "dataset", target)


if __name__ == "__main__":
    unittest.main()
