"""Synthetic rules for stream identity, continuation, cadence, and amounts."""

import sys
import unittest
from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))

from buy_or_wait.domain import UnsupportedCase
from buy_or_wait.reconciliation import reconcile
from buy_or_wait.streams import (Continuation, StreamMode, StreamPolicy,
                                 estimate_amount, identity_for, infer_cadence,
                                 resolve_streams)
from test_forecast import context, event


def salary(identifier, when, amount, label):
    return replace(event(identifier, when, amount, direction="credit"), description=label)


class StreamIdentityTest(unittest.TestCase):
    def test_distinct_salary_sources_remain_separate(self):
        events = tuple(salary(f"a{i}", date(2026, i, 10), "100", "Employer A") for i in (1, 2, 3))
        events += tuple(salary(f"b{i}", date(2026, i, 20), "80", "Employer B") for i in (1, 2, 3))
        streams = resolve_streams(reconcile(context(events)), date(2026, 4, 3), date(2026, 7, 2))
        active = [stream for stream in streams if stream.continuation == Continuation.CONTINUING]
        self.assertEqual({stream.identity.label for stream in active}, {"employer a", "employer b"})
        self.assertEqual({stream.amount for stream in active}, {Decimal("100"), Decimal("80")})

    def test_same_behavior_groups_but_unrelated_fixed_expenses_do_not(self):
        groceries = tuple(replace(event(f"g{i}", date(2026, 3, 4 + 7 * i)),
                                  category="groceries", description=f"Shop {i}") for i in range(3))
        rent = event("rent", date(2026, 3, 1))
        utility = replace(event("utility", date(2026, 3, 2)), category="utilities",
                          description="Power bill")
        streams = resolve_streams(reconcile(context(groceries + (rent, utility))),
                                  date(2026, 4, 3), date(2026, 7, 2))
        behavior = [s for s in streams if s.identity.mode == StreamMode.SPENDING_BEHAVIOR]
        self.assertEqual(len(behavior), 1)
        self.assertEqual(len(behavior[0].source_event_ids), 3)
        fixed = [s for s in streams if s.identity.mode == StreamMode.TRANSACTION]
        self.assertEqual(len(fixed), 2)

    def test_lifecycle_replacement_does_not_duplicate_stream_history(self):
        prior = tuple(event(str(i), date(2026, i, 6)) for i in (1, 2))
        old = event("old", date(2026, 3, 5), status="failed")
        new = event("new", date(2026, 3, 6), linked="old")
        streams = resolve_streams(reconcile(context(prior + (old, new))),
                                  date(2026, 4, 3), date(2026, 7, 2))
        self.assertEqual(len(streams), 1)
        self.assertEqual(streams[0].source_event_ids, ("1", "2", "new"))

    def test_singleton_is_one_time_and_never_projected(self):
        streams = resolve_streams(reconcile(context((event("only", date(2026, 3, 1)),))),
                                  date(2026, 4, 3), date(2026, 7, 2))
        self.assertEqual(streams[0].continuation, Continuation.ONE_TIME)
        self.assertEqual(streams[0].next_projected_dates, ())


class CadenceAndAmountTest(unittest.TestCase):
    def test_weekly_biweekly_and_monthly(self):
        self.assertEqual(infer_cadence(tuple(date(2026, 1, 1) + timedelta(days=7*i) for i in range(3))).name, "weekly")
        self.assertEqual(infer_cadence(tuple(date(2026, 1, 1) + timedelta(days=14*i) for i in range(3))).name, "biweekly")
        self.assertEqual(infer_cadence((date(2026, 1, 15), date(2026, 2, 15), date(2026, 3, 15))).name, "monthly")

    def test_small_drift_and_ambiguity(self):
        cadence = infer_cadence((date(2026, 1, 1), date(2026, 1, 9), date(2026, 1, 15)))
        self.assertEqual(cadence.name, "weekly")
        with self.assertRaisesRegex(UnsupportedCase, "inconsistent"):
            infer_cadence((date(2026, 1, 1), date(2026, 1, 8), date(2026, 2, 3)))
        with self.assertRaisesRegex(UnsupportedCase, "insufficient"):
            infer_cadence((date(2026, 1, 1), date(2026, 1, 8)))

    def test_amount_estimation_is_separate_and_directional(self):
        debits = tuple(replace(event(str(i), date(2026, i, 1)), amount=Decimal(value))
                       for i, value in zip((1, 2, 3), ("10", "30", "20")))
        credits = tuple(replace(item, direction="credit", event_type="income", category="salary")
                        for item in debits)
        self.assertEqual(estimate_amount(debits), (Decimal("30"), "conservative_max_observed_expense"))
        self.assertEqual(estimate_amount(debits, conservative_expense=False),
                         (Decimal("20"), "observed_mean_flexible_expense"))
        self.assertEqual(estimate_amount(credits), (Decimal("10"), "conservative_min_observed_income"))

    def test_variable_behavior_uses_only_cadence_derived_occurrences(self):
        from buy_or_wait.forecast import build_forecast
        groceries = tuple(replace(event(f"g{i}", date(2026, 3, 13 + 7 * i), str(value)),
                                  category="groceries", description=f"Shop {i}")
                          for i, value in enumerate(("10", "12", "11")))
        timeline = build_forecast(context(groceries))
        contingency = [entry for entry in timeline.entries
                       if entry.basis.startswith("behavior_contingency")]
        self.assertEqual(contingency, [])

    def test_same_day_behavior_events_form_one_daily_observation(self):
        groceries = (
            replace(event("g1", date(2026, 3, 1), "10"), category="groceries"),
            replace(event("g2", date(2026, 3, 1), "5"), category="groceries"),
            replace(event("g3", date(2026, 3, 8), "12"), category="groceries"),
            replace(event("g4", date(2026, 3, 15), "11"), category="groceries"),
        )
        stream = resolve_streams(reconcile(context(groceries)),
                                 date(2026, 3, 22), date(2026, 4, 12))[0]
        self.assertEqual(stream.observed_dates,
                         (date(2026, 3, 1), date(2026, 3, 8), date(2026, 3, 15)))
        self.assertEqual(stream.cadence.name, "weekly")
        self.assertEqual(stream.amount, Decimal("38") / Decimal("3"))
        self.assertEqual(stream.amount_policy, "observed_mean_flexible_daily_expense")
        self.assertEqual(set(stream.source_event_ids), {"g1", "g2", "g3", "g4"})


class ContinuationTest(unittest.TestCase):
    def test_one_salary_terminated_without_ending_another(self):
        a = tuple(salary(f"a{i}", date(2026, i, 10), "100", "Employer A") for i in (1, 2, 3))
        b = tuple(salary(f"b{i}", date(2026, i, 20), "80", "Employer B") for i in (1, 2, 3))
        terminal = salary("final", date(2026, 4, 10), "100", "Final employer payroll")
        streams = resolve_streams(reconcile(context(a + b + (terminal,))),
                                  date(2026, 4, 15), date(2026, 7, 14))
        states = {stream.identity.label: stream.continuation for stream in streams}
        self.assertEqual(states["employer a"], Continuation.TERMINATED)
        self.assertEqual(states["employer b"], Continuation.CONTINUING)

    def test_variable_income_calendar_slots_remain_independent(self):
        events = tuple(salary(f"x{i}", date(2026, i, 7), str(100+i), f"Contract {i}") for i in (1, 2, 3))
        events += tuple(salary(f"y{i}", date(2026, i, 20), str(80+i), f"Project {i}") for i in (1, 2, 3))
        streams = resolve_streams(reconcile(context(events)), date(2026, 4, 3), date(2026, 7, 2))
        self.assertEqual({s.identity.label for s in streams}, {"calendar_slot:7", "calendar_slot:20"})
        self.assertEqual({s.amount for s in streams}, {Decimal("101"), Decimal("81")})

    def test_uncertain_income_is_excluded_but_uncertain_expense_blocks(self):
        dates = (date(2026, 1, 1), date(2026, 1, 8), date(2026, 2, 9))
        income = tuple(salary(str(i), when, "100", "Employer") for i, when in enumerate(dates))
        expense = tuple(event(str(i), when) for i, when in enumerate(dates))
        income_stream = resolve_streams(reconcile(context(income)), date(2026, 4, 3), date(2026, 7, 2))[0]
        expense_stream = resolve_streams(reconcile(context(expense)), date(2026, 4, 3), date(2026, 7, 2))[0]
        self.assertEqual(income_stream.continuation, Continuation.INSUFFICIENT)
        self.assertEqual(expense_stream.continuation, Continuation.INSUFFICIENT)
        from buy_or_wait.forecast import build_forecast
        self.assertEqual(build_forecast(context(income)).entries, ())
        with self.assertRaisesRegex(UnsupportedCase, "inconsistent"):
            build_forecast(context(expense))

    def test_missing_expected_occurrence_does_not_assume_continuation(self):
        income = tuple(salary(str(i), date(2026, i, 15), "100", "Employer")
                       for i in (1, 2, 3))
        streams = resolve_streams(reconcile(context(income)), date(2026, 5, 3), date(2026, 8, 1))
        self.assertEqual(streams[0].continuation, Continuation.INSUFFICIENT)
        self.assertIn("expected occurrence", streams[0].continuation_reason)


if __name__ == "__main__":
    unittest.main()
