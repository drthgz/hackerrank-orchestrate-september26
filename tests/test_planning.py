"""Independent deterministic planning and candidate-policy tests."""

import sys
import unittest
from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))

from buy_or_wait.domain import Method, Payment, PaymentOption, Status
from buy_or_wait.forecast import ForecastEntry, ForecastPolicy, ForecastTimeline, build_forecast
from buy_or_wait.planning import (Candidate, _base_candidates, _evaluate, _rank_key,
                                  earliest_safe_full_date, plan, safe_capacity)
from test_forecast import context, event


def timeline(opening="100", minimum="20", entries=()):
    start = date(2026, 4, 3)
    return ForecastTimeline(start, start + timedelta(days=90), Decimal(opening),
                            Decimal(minimum), tuple(entries), ForecastPolicy())


def configured(amount="60", methods=(Method.FULL,), partial=False, deadline_days=60,
               options=None, balance="100", minimum="20"):
    base = context(())
    request = replace(base.request, requested_amount=Decimal(amount),
                      allows_partial_payment=partial,
                      desired_completion_date=base.request.request_date + timedelta(days=deadline_days))
    profile = replace(base.profile, balance=Decimal(balance), minimum=Decimal(minimum),
                      methods=frozenset(methods))
    if options is None:
        options = (PaymentOption("full", Method.FULL, Decimal(amount), 1,
                                 request.request_date, None, Decimal("0"), Decimal(amount)),)
    return replace(base, request=request, profile=profile, options=tuple(options))


class CapacityTest(unittest.TestCase):
    def test_full_payment_success_and_reserve_equality(self):
        ctx = configured(amount="80")
        result = plan(ctx, timeline())
        self.assertEqual(result.amount_safe_today, Decimal("80.00"))
        self.assertEqual(result.prediction.affordability_status, Status.NOW)
        self.assertEqual(result.evaluations[0].minimum_projected_balance, Decimal("20"))

    def test_full_payment_fails_due_to_later_violation(self):
        entry = ForecastEntry(date(2026, 4, 10), Decimal("-30"), "bill", (), "explicit")
        result = plan(configured(), timeline(entries=(entry,)))
        full = next(item for item in result.evaluations if item.candidate.method == Method.FULL)
        self.assertFalse(full.eligible)
        self.assertEqual(full.rejection_reason, "minimum-balance simulation failed")

    def test_safe_capacity_uses_simulation(self):
        entries = (ForecastEntry(date(2026, 4, 3), Decimal("-10"), "debit", (), "explicit"),
                   ForecastEntry(date(2026, 4, 3), Decimal("20"), "credit", (), "explicit"))
        self.assertEqual(safe_capacity(timeline(entries=entries), Decimal("100")), Decimal("70.00"))

    def test_earliest_safe_date_and_no_safe_date(self):
        credit = ForecastEntry(date(2026, 4, 8), Decimal("50"), "credit", (), "explicit")
        self.assertEqual(earliest_safe_full_date(timeline(entries=(credit,)), Decimal("100")),
                         date(2026, 4, 9))  # Same-day payment precedes credit.
        self.assertIsNone(earliest_safe_full_date(timeline(), Decimal("81")))


class StrategyTest(unittest.TestCase):
    def test_wait_eligible_and_deadline_rejected(self):
        credit = ForecastEntry(date(2026, 4, 8), Decimal("50"), "credit", (), "explicit")
        result = plan(configured(amount="100"), timeline(entries=(credit,)))
        self.assertEqual(result.prediction.recommended_payment_method, Method.WAIT)
        self.assertEqual(result.prediction.payment_plan[0].date, date(2026, 4, 9))
        late = plan(configured(amount="100", deadline_days=5), timeline(entries=(credit,)))
        self.assertEqual(late.prediction.recommended_payment_method, Method.NO)

    def test_valid_partial_and_unsafe_arbitrary_remainder(self):
        debit = ForecastEntry(date(2026, 4, 4), Decimal("-30"), "debit", (), "explicit")
        credit = ForecastEntry(date(2026, 4, 8), Decimal("80"), "credit", (), "explicit")
        ctx = configured(amount="80", methods=(Method.PARTIAL,), partial=True)
        result = plan(ctx, timeline(entries=(debit, credit)))
        self.assertEqual(result.prediction.recommended_payment_method, Method.PARTIAL)
        self.assertEqual(result.prediction.payment_plan,
                         (Payment(date(2026, 4, 3), Decimal("50.00")),
                          Payment(date(2026, 4, 9), Decimal("30.00"))))
        arbitrary = Candidate(Method.PARTIAL,
                              (Payment(date(2026, 4, 3), Decimal("50")),
                               Payment(date(2026, 4, 4), Decimal("30"))),
                              total_paid=Decimal("80"))
        self.assertFalse(_evaluate(ctx, timeline(entries=(debit, credit)), arbitrary).eligible)

    def test_partial_after_deadline_rejected(self):
        credit = ForecastEntry(date(2026, 4, 20), Decimal("80"), "credit", (), "explicit")
        result = plan(configured(amount="80", methods=(Method.PARTIAL,), partial=True,
                                 deadline_days=10), timeline(entries=(credit,)))
        self.assertEqual(result.prediction.recommended_payment_method, Method.NO)

    def test_valid_and_unsafe_supplied_installments(self):
        start = date(2026, 4, 3)
        option = PaymentOption("install", Method.INSTALLMENTS, Decimal("30"), 2,
                               start, 30, Decimal("0"), Decimal("60"))
        ctx = configured(methods=(Method.INSTALLMENTS,), options=(option,))
        ctx = replace(ctx, profile=replace(ctx.profile, max_installment_months=2))
        self.assertEqual(plan(ctx, timeline()).prediction.recommended_payment_method, Method.INSTALLMENTS)
        debit = ForecastEntry(start + timedelta(days=20), Decimal("-30"), "bill", (), "explicit")
        self.assertEqual(plan(ctx, timeline(entries=(debit,))).prediction.recommended_payment_method, Method.NO)

    def test_installment_option_is_not_invented(self):
        ctx = configured(methods=(Method.INSTALLMENTS,), options=())
        self.assertEqual(_base_candidates(ctx, Decimal("60"), ctx.request.request_date), ())
        self.assertEqual(plan(ctx, timeline()).prediction.recommended_payment_method, Method.NO)


class RankingTest(unittest.TestCase):
    def test_no_changes_then_cost_then_start_and_fewer_payments(self):
        now = date(2026, 4, 3)
        candidates = [
            Candidate(Method.INSTALLMENTS, (Payment(now, Decimal("30")), Payment(now + timedelta(days=1), Decimal("30"))), option_id="b", total_paid=Decimal("60")),
            Candidate(Method.WAIT, (Payment(now + timedelta(days=2), Decimal("60")),), total_paid=Decimal("60")),
        ]
        from buy_or_wait.planning import CandidateEvaluation
        evaluations = [CandidateEvaluation(item, True, None, Decimal("20"), item.payments[-1].date) for item in candidates]
        self.assertEqual(sorted(evaluations, key=_rank_key)[0].candidate.method, Method.INSTALLMENTS)


class SpendingChangeTest(unittest.TestCase):
    def recurring_context(self, *, flexibility, minimum_allowed=None, protected=False,
                          amount="40", categories=("cloud_storage",)):
        events = []
        for category in categories:
            for month in (1, 2, 3):
                item = replace(event(f"{category}-{month}", date(2026, month, 6), "20"),
                               category=category, description=f"{category} subscription",
                               event_type="subscription", flexibility=flexibility,
                               minimum_allowed_amount=Decimal(minimum_allowed) if minimum_allowed else None)
                events.append(item)
        ctx = configured(amount=amount, balance="100" if len(categories) == 1 else "160")
        profile = replace(ctx.profile,
                          protected=frozenset(categories) if protected else frozenset(),
                          reduce_categories=frozenset(categories),
                          stop_categories=frozenset(categories))
        return replace(ctx, profile=profile, events=tuple(events))

    def test_flexible_stop_and_reduction(self):
        stopped = self.recurring_context(flexibility="stoppable", amount="60")
        stopped_result = plan(stopped, build_forecast(stopped))
        self.assertEqual(stopped_result.prediction.spending_changes_needed[0].action, "stop")
        self.assertEqual(stopped_result.prediction.affordability_status, Status.PLAN)

        reduced = self.recurring_context(flexibility="reducible", minimum_allowed="5")
        reduced_result = plan(reduced, build_forecast(reduced))
        self.assertEqual(reduced_result.prediction.spending_changes_needed[0].action, "reduce_to")
        self.assertEqual(reduced_result.prediction.spending_changes_needed[0].new_amount, Decimal("5"))

        either = self.recurring_context(flexibility="reducible_or_stoppable", minimum_allowed="5")
        either_result = plan(either, build_forecast(either))
        self.assertTrue(any(item.candidate.changes[0].action == "stop"
                            for item in either_result.evaluations if item.candidate.changes))
        self.assertTrue(any(item.candidate.changes[0].action == "reduce_to"
                            for item in either_result.evaluations if item.candidate.changes))

    def test_fixed_or_protected_expense_cannot_change(self):
        for ctx in (self.recurring_context(flexibility="fixed"),
                    self.recurring_context(flexibility="stoppable", protected=True)):
            with self.subTest(profile=ctx.profile):
                result = plan(ctx, build_forecast(ctx))
                self.assertEqual(result.prediction.recommended_payment_method, Method.NO)
                self.assertFalse(any(item.candidate.changes for item in result.evaluations))

    def test_minimum_number_of_changes_is_selected(self):
        ctx = self.recurring_context(flexibility="stoppable", amount="100",
                                     categories=("cloud_storage", "streaming"))
        result = plan(ctx, build_forecast(ctx))
        self.assertEqual(len(result.prediction.spending_changes_needed), 2)
        one_change = [item for item in result.evaluations if len(item.candidate.changes) == 1]
        self.assertTrue(one_change and all(not item.eligible for item in one_change))


if __name__ == "__main__":
    unittest.main()
