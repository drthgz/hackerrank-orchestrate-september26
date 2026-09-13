"""Independent synthetic regressions for cash state and financial lifecycles."""

import sys
import unittest
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))

from buy_or_wait.domain import CashKind, DataError, FxRate, Payment, UnsupportedCase
from buy_or_wait.fx import to_home
from buy_or_wait.forecast import build_forecast, simulate
from buy_or_wait.loading import RawContext, SCHEMAS
from buy_or_wait.normalize import normalize
from buy_or_wait.reconciliation import ended_streams, reconcile
from test_forecast import context, event


class TerminalPayrollTest(unittest.TestCase):
    def salary(self):
        return tuple(event(str(month), date(2026, month, 15), "100", direction="credit") for month in (1, 2, 3))

    def test_final_payroll_overrides_repeated_history(self):
        salary = self.salary()
        salary = salary[:-1] + (replace(salary[-1], description="Final employer payroll"),)
        ctx = context(salary)
        self.assertEqual(ended_streams(ctx)[0].source_ids, ("3",))
        forecast = build_forecast(ctx)
        self.assertEqual(forecast.entries, ())
        self.assertEqual(simulate(forecast).minimum_balance, ctx.profile.balance)

    def test_marker_is_exact_not_substring_guess(self):
        salary = self.salary()
        ctx = context(tuple(replace(item, description="Not final employer payroll") for item in salary))
        self.assertEqual(ended_streams(ctx), ())
        self.assertEqual(sum(e.amount for e in build_forecast(ctx).entries), Decimal("300"))

    def test_later_income_after_terminal_marker_is_unresolved(self):
        salary = self.salary()
        ctx = context(salary[:-1] + (replace(salary[-1], description="Final employer payroll"),
                      event("future", date(2026, 4, 15), "100", direction="credit", status="scheduled")))
        with self.assertRaisesRegex(UnsupportedCase, "terminated payroll"):
            build_forecast(ctx)


class NonCashTest(unittest.TestCase):
    def raw(self, **changes):
        value = dict(zip(SCHEMAS["financial_events"], (
            "valuation", "u", "investment_valuation", "Portfolio valuation", "investment",
            "non_cash", "99999999", "EUR", "2026-04-02", "", "unrealized", "", "fixed", "",
        )))
        value.update(changes)
        return RawContext(
            dict(request_id="r", user_id="u", request_date="2026-04-03", request_type="purchase", requested_amount="10", desired_completion_date="2026-04-20", allows_partial_payment="false", request_text="Purchase"),
            dict(zip(SCHEMAS["financial_profiles"], ("u", "EUR", "100", "10", "savings", "rent", "", "", "full_payment", ""))),
            (value,), (), (), (), (),
        )

    def test_valid_non_cash_normalizes_without_settlement_date(self):
        normalized = normalize(self.raw())
        self.assertEqual(normalized.events[0].cash_kind, CashKind.INFORMATIONAL)
        self.assertIsNone(normalized.events[0].settlement_date)

    def test_non_cash_value_never_changes_balance_or_capacity(self):
        empty = context(())
        expected = simulate(build_forecast(empty))
        for value in ("1", "999999999999999999999", ""):
            normalized = normalize(self.raw(amount=value))
            actual = simulate(build_forecast(replace(empty, events=normalized.events)))
            self.assertEqual(actual, expected)
            self.assertEqual(actual.minimum_balance - empty.profile.minimum, Decimal("90"))

    def test_malformed_combinations_are_rejected(self):
        for changes in (dict(direction="credit"), dict(status="settled"), dict(event_type="income"), dict(event_type="unknown"), dict(direction="debit", event_type="expense")):
            with self.subTest(changes=changes), self.assertRaises(DataError):
                normalize(self.raw(**changes))


class LifecycleTest(unittest.TestCase):
    def test_cancelled_authorization_and_failed_retry_keep_successor_once(self):
        for state in ("cancelled", "failed"):
            with self.subTest(state=state):
                old = event("old", date(2026, 4, 5), "12", status=state)
                new = event("new", date(2026, 4, 6), "12", status="scheduled", linked="old")
                resolved = reconcile(context((old, new)))
                self.assertEqual([e.event_id for e in resolved.events], ["new"])
                self.assertEqual(next(t for t in resolved.treatments if t.event_id == "old").interpretation, "replaced")
                self.assertEqual(simulate(build_forecast(resolved)).minimum_balance, Decimal("88"))
                self.assertEqual(build_forecast(resolved).entries[0].source_ids, ("old", "new"))

    def test_pending_to_future_settled_keeps_hold_and_releases_difference_later(self):
        old = event("hold", date(2026, 4, 5), "80", status="pending")
        new = event("posted", date(2026, 4, 6), "60", linked="hold")
        resolved = reconcile(context((old, new)))
        timeline = build_forecast(resolved)
        result = simulate(timeline)
        self.assertEqual([(p.date, p.balance) for p in result.points], [
            (date(2026, 4, 3), Decimal("100")), (date(2026, 4, 3), Decimal("20")),
            (date(2026, 4, 6), Decimal("40"))])
        self.assertFalse(simulate(timeline, (Payment(date(2026, 4, 3), Decimal("11")),)).safe)

    def test_already_settled_replacement_does_not_keep_old_hold(self):
        old = event("hold", date(2026, 3, 1), "80", status="pending")
        new = event("posted", date(2026, 3, 2), "60", linked="hold")
        resolved = reconcile(context((old, new)))
        self.assertEqual(resolved.events[0].status, "settled")
        self.assertEqual(resolved.events[0].amount, Decimal("60"))
        self.assertEqual(resolved.reservation_releases, ())

    def test_refund_or_reversal_keeps_original_cash_movement(self):
        debit = event("purchase", date(2026, 4, 5), "30")
        refund = replace(event("refund", date(2026, 4, 6), "30", direction="credit", linked="purchase"), event_type="refund", category="rent")
        resolved = reconcile(context((debit, refund)))
        self.assertEqual(len(resolved.events), 2)
        points = simulate(build_forecast(resolved)).points
        self.assertEqual([p.balance for p in points], [Decimal("100"), Decimal("70"), Decimal("100")])
        self.assertEqual(next(t for t in resolved.treatments if t.event_id == "refund").source_ids, ("purchase", "refund"))

    def test_pending_refund_never_releases_original_debit(self):
        debit = event("purchase", date(2026, 4, 5), "30")
        refund = replace(event("refund", date(2026, 4, 6), "30", direction="credit", status="pending", linked="purchase"), event_type="refund", category="rent")
        resolved = reconcile(context((debit, refund)))
        self.assertFalse(next(t for t in resolved.treatments if t.event_id == "refund").cash_affecting)
        self.assertEqual(simulate(build_forecast(resolved)).points[-1].balance, Decimal("70"))

    def test_historical_refund_is_not_inferred_income(self):
        debits = tuple(event(str(i), date(2026, i, 6), "10") for i in (1, 2, 3))
        refund = replace(event("refund", date(2026, 3, 7), "10", direction="credit", linked="3"), event_type="refund", category="rent")
        self.assertTrue(all(e.amount < 0 for e in build_forecast(reconcile(context(debits + (refund,)))).entries))

    def test_investment_valuation_and_sale_are_distinct_from_purchase(self):
        purchase = replace(event("buy", date(2026, 4, 5), "20"), event_type="investment_purchase", category="investment")
        valuation = replace(event("value", date(2026, 4, 6), "9999", linked="buy"), event_type="investment_valuation", category="investment", direction="non_cash", status="unrealized", settlement_date=None)
        sale = replace(event("sale", date(2026, 4, 7), "25", direction="credit", linked="value"), event_type="investment_sale", category="investment")
        resolved = reconcile(context((purchase, valuation, sale)))
        self.assertEqual([e.event_id for e in resolved.events], ["buy", "sale"])
        self.assertEqual(simulate(build_forecast(resolved)).points[-1].balance, Decimal("105"))
        self.assertEqual(next(t for t in resolved.treatments if t.event_id == "value").interpretation, "informational")

    def test_possible_duplicate_is_reserved_not_silently_dropped(self):
        debit = event("original", date(2026, 4, 5), "20")
        duplicate = event("possible", date(2026, 4, 6), "20", status="pending", linked="original")
        resolved = reconcile(context((debit, duplicate)))
        self.assertEqual(len(resolved.events), 2)
        self.assertEqual(simulate(build_forecast(resolved)).minimum_balance, Decimal("60"))

    def test_unknown_links_cycles_and_multiple_replacements_fail(self):
        a = event("a", date(2026, 4, 5))
        b = event("b", date(2026, 4, 6), linked="a")
        with self.assertRaises(UnsupportedCase):
            reconcile(context((a, b)))  # Two settled debits do not prove duplication.
        with self.assertRaises(DataError):
            reconcile(context((replace(a, linked_event_id="b"), b)))
        old = replace(a, status="failed")
        with self.assertRaises(UnsupportedCase):
            reconcile(context((old, b, replace(b, event_id="c"))))

    def test_reconciliation_is_independent_of_input_order(self):
        a = event("a", date(2026, 4, 5), status="cancelled")
        b = event("b", date(2026, 4, 6), linked="a")
        self.assertEqual(reconcile(context((a, b))).treatments, reconcile(context((b, a))).treatments)


class FxTest(unittest.TestCase):
    def test_settlement_date_and_direction_are_exact(self):
        rates = (FxRate(date(2026, 4, 4), "USD", "EUR", Decimal("0.8")),
                 FxRate(date(2026, 4, 5), "USD", "EUR", Decimal("0.9")))
        movement = replace(event("foreign", date(2026, 4, 5), "10", status="pending"), currency="USD", event_date=date(2026, 4, 4))
        timeline = build_forecast(replace(context((movement,)), rates=rates))
        self.assertEqual(timeline.entries[0].amount, Decimal("-9.0"))
        self.assertEqual(timeline.entries[0].date, timeline.start)  # Reservation today, FX at settlement.
        self.assertIn("fx:2026-04-05:USD:EUR", timeline.entries[0].source_ids)
        with self.assertRaises(UnsupportedCase):
            to_home(Decimal("10"), "EUR", "USD", date(2026, 4, 5), rates)

    def test_each_inferred_settlement_uses_its_own_rate(self):
        salary = tuple(replace(event(str(i), date(2026, i, 15), "100", direction="credit"), currency="USD") for i in (1, 2, 3))
        rates = tuple(FxRate(date(2026, month, 15), "USD", "EUR", Decimal(rate)) for month, rate in ((4, "0.8"), (5, "0.9"), (6, "1.0")))
        ctx = replace(context(salary), rates=rates)
        self.assertEqual([e.amount for e in build_forecast(ctx).entries], [Decimal("80"), Decimal("90"), Decimal("100")])
        with self.assertRaises(UnsupportedCase):
            build_forecast(replace(ctx, rates=rates[:2]))

    def test_conversion_keeps_decimal_precision(self):
        rate = FxRate(date(2026, 4, 5), "USD", "EUR", Decimal("0.3"))
        self.assertEqual(to_home(Decimal("0.1"), "USD", "EUR", rate.settlement_date, (rate,))[0], Decimal("0.03"))
