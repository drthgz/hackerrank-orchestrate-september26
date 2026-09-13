"""Provisional vertical-slice policy, replaceable after sample evaluation.

No CSV knowledge, evidence interpretation, label access, or payment selection.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from .domain import CashKind, Event, FinancialContext, Payment, UnsupportedCase
from .reconciliation import ResolvedContext, reconcile
from .fx import to_home
from .streams import (Continuation, StreamMode, StreamPolicy, identity_for, infer_cadence,
                      estimate_amount, project_dates, resolve_streams)


@dataclass(frozen=True)
class ForecastPolicy:
    """v1 assumptions: all supplied past settled history; streams grouped by
    structured type/category/direction; monthly slots or exact fixed cadence;
    maximum expense/minimum income; no optional spending reductions; explicit
    same-key/date occurrence wins (including pending credit); unknowns fail.

    Calendar slots after day 28, evidence, FX, overdue/stale streams, and complex
    lifecycle resolution are deliberately unsupported. These choices are policy,
    not loader/serializer behavior or final challenge interpretations.
    """
    version: str = "recurring-streams-v1"
    horizon_days: int = 90  # Include request date and the day at +90.
    min_occurrences: int = 3
    min_months: int = 3
    max_monthly_slots: int = 2
    last_supported_monthly_day: int = 28
    max_relative_amount_deviation: Decimal = Decimal("0.35")
    fixed_intervals: tuple[int, ...] = (7, 10, 14, 21, 28)
    # Provisional cash snapshot: past settled events already included; pending
    # debits reserved today. Same-day candidate payments precede all credits.
    debit_priority: int = 0
    payment_priority: int = 1
    credit_priority: int = 2
    stream_policy: StreamPolicy = StreamPolicy()


@dataclass(frozen=True)
class ForecastEntry:
    date: date
    amount: Decimal  # Signed, in home currency.
    entry_id: str
    source_ids: tuple[str, ...]
    basis: str


@dataclass(frozen=True)
class ForecastTimeline:
    start: date
    end: date
    opening_balance: Decimal
    minimum_balance: Decimal
    entries: tuple[ForecastEntry, ...]
    policy: ForecastPolicy
    streams: tuple = ()


@dataclass(frozen=True)
class BalancePoint:
    date: date
    entry_id: str
    balance: Decimal


@dataclass(frozen=True)
class Simulation:
    points: tuple[BalancePoint, ...]
    minimum_balance: Decimal
    safe: bool


def infer_occurrences(history: tuple[Event, ...], start: date, end: date,
                      policy: ForecastPolicy) -> tuple[tuple[date, Decimal], ...]:
    """Compatibility wrapper around separated identity/cadence/amount policies."""
    if len({identity_for(e, policy.stream_policy) for e in history}) != 1:
        raise UnsupportedCase("Mixed financial streams")
    ordered = sorted(history, key=lambda e: (e.settlement_date or date.min, e.event_id))
    if any(e.amount is None or e.amount <= 0 or e.settlement_date is None for e in ordered):
        raise UnsupportedCase("Recurrence has missing/zero amount or date")
    cadence = infer_cadence(tuple(e.settlement_date for e in ordered), policy.stream_policy)
    amount, _ = estimate_amount(tuple(ordered))
    return tuple((when, amount) for when in project_dates(ordered[-1].settlement_date,
                                                          cadence, start, end))


def build_forecast(context: FinancialContext | ResolvedContext,
                   policy: ForecastPolicy = ForecastPolicy()) -> ForecastTimeline:
    # Compatibility for direct callers; the application invokes reconciliation
    # as its own stage and passes a ResolvedContext. No lifecycle logic lives here.
    resolved = context if isinstance(context, ResolvedContext) else reconcile(context)
    context = resolved.context
    resolved_evidence = {fact.source.source_id for fact in context.extracted_facts}
    unresolved_evidence = [item.source.source_id for item in context.evidence
                           if item.source.source_id not in resolved_evidence]
    if unresolved_evidence:
        raise UnsupportedCase("Uninterpreted messages/images require later extraction")
    if any(e.amount is None for e in resolved.events):
        raise UnsupportedCase("Missing financial amount remains unresolved")
    start = context.request.request_date
    end = start + timedelta(days=policy.horizon_days)
    explicit = {}
    entries = []
    treatments = {item.event_id: item for item in resolved.treatments}
    for event in resolved.events:
        when = event.settlement_date
        if when is None:
            raise UnsupportedCase("Active cash event is missing settlement date")
        if event.status == "settled" and when < start:
            continue
        if when < start and event.status != "pending":
            raise UnsupportedCase("Overdue scheduled cash event needs reconciliation")
        if event.status == "settled" and when == start:
            raise UnsupportedCase("Same-day settled event snapshot is unresolved")
        if when > end and event.status != "pending":
            continue
        identity = identity_for(event, policy.stream_policy)
        key = (identity, when)
        if key in explicit:
            raise UnsupportedCase("Multiple explicit records for one occurrence")
        explicit[key] = event
        if not treatments[event.event_id].cash_affecting:
            continue  # Also suppresses inference for its explicit occurrence.
        if event.direction == "credit" and event.status != "settled" and not (event.event_type == "income" and event.category == "salary"):
            raise UnsupportedCase("Future non-salary credit needs cash-state resolution")
        cash_date = start if event.status == "pending" else when
        sign = Decimal("-1") if event.direction == "debit" else Decimal("1")
        converted, rate_sources = to_home(event.amount, event.currency, context.profile.currency, when, context.rates)
        entries.append(ForecastEntry(cash_date, sign * converted, event.event_id, treatments[event.event_id].source_ids + rate_sources, "explicit"))
    streams = resolve_streams(resolved, start, end, policy.stream_policy)
    explicit_occurrences = {(event.event_type, event.category, event.direction,
                             event.currency, event.settlement_date): event
                            for event in resolved.events if event.settlement_date is not None
                            and event.settlement_date >= start}
    for stream in streams:
        if stream.continuation in {Continuation.TERMINATED, Continuation.ONE_TIME,
                                    Continuation.SUPERSEDED}:
            continue
        if stream.continuation == Continuation.INSUFFICIENT:
            if stream.identity.direction == "debit":
                raise UnsupportedCase(f"Stream {stream.identity.diagnostic_id()}: {stream.continuation_reason}")
            continue  # Uncertain income never increases capacity.
        if stream.identity.direction == "credit" and (stream.identity.event_type,
                                                       stream.identity.category) != ("income", "salary"):
            raise UnsupportedCase("Only repeated structured salary income is supported")
        if stream.identity.mode == StreamMode.SPENDING_BEHAVIOR:
            # Category-level behavior is less exact than a billed transaction.
            # Reserve one extra maximum observation at the request boundary so
            # timing/count uncertainty cannot create spendable capacity.
            converted, rate_sources = to_home(stream.amount, stream.identity.currency,
                                              context.profile.currency, start, context.rates)
            entries.append(ForecastEntry(start, -converted,
                                         f"behavior-contingency:{stream.identity.diagnostic_id()}",
                                         stream.source_event_ids + rate_sources,
                                         f"behavior_contingency:{stream.amount_policy}"))
        for occurrence_index, when in enumerate(stream.next_projected_dates):
            broad = (stream.identity.event_type, stream.identity.category,
                     stream.identity.direction, stream.identity.currency, when)
            if broad in explicit_occurrences:
                continue
            amount = stream.amount
            amendment_sources = ()
            terminated = False
            for fact in context.extracted_facts:
                matches = (fact.category == stream.identity.category
                           and fact.direction == stream.identity.direction)
                if not matches:
                    continue
                if (fact.fact_type == "stream_termination" and fact.effective_date is not None
                        and when >= fact.effective_date):
                    terminated = True
                effective = fact.effective_date is None or when >= fact.effective_date
                selected_occurrence = (fact.scope == "ongoing" or
                                       (fact.scope == "one_occurrence" and occurrence_index == 0))
                if fact.fact_type == "stream_amount" and effective and selected_occurrence:
                    amount = Decimal(fact.value)
                    amendment_sources += (fact.source.source_id,)
                if fact.fact_type == "stream_percent_change" and effective and selected_occurrence:
                    factor = Decimal("1") + Decimal(fact.value) / Decimal("100")
                    amount = amount * factor
                    amendment_sources += (fact.source.source_id,)
            if terminated:
                continue
            sign = Decimal("-1") if stream.identity.direction == "debit" else Decimal("1")
            converted, rate_sources = to_home(amount, stream.identity.currency,
                                              context.profile.currency, when, context.rates)
            entries.append(ForecastEntry(when, sign * converted,
                                         f"inferred:{stream.identity.diagnostic_id()}:{when}",
                                         stream.source_event_ids + amendment_sources + rate_sources,
                                         f"recurrence:{stream.cadence.name}:{stream.amount_policy}"))
    for release in resolved.reservation_releases:
        if start <= release.date <= end:
            converted, rate_sources = to_home(release.amount, release.currency, context.profile.currency, release.date, context.rates)
            entries.append(ForecastEntry(release.date, converted, f"reservation-release:{release.source_ids[-1]}", release.source_ids + rate_sources, "reservation_release"))
    return ForecastTimeline(start, end, context.profile.balance, context.profile.minimum,
                            tuple(sorted(entries, key=lambda e: (e.date, e.entry_id))), policy,
                            streams)


def simulate(timeline: ForecastTimeline, payments: tuple[Payment, ...] = ()) -> Simulation:
    policy = timeline.policy
    movements = [(e.date, policy.debit_priority if e.amount < 0 else policy.credit_priority, e.entry_id, e.amount) for e in timeline.entries]
    for i, payment in enumerate(payments):
        if not timeline.start <= payment.date <= timeline.end or not payment.amount.is_finite() or payment.amount <= 0:
            raise ValueError("Candidate payment outside forecast bounds")
        movements.append((payment.date, policy.payment_priority, f"payment:{i}", -payment.amount))
    balance = timeline.opening_balance
    points = [BalancePoint(timeline.start, "opening", balance)]
    for when, _, identifier, amount in sorted(movements):
        balance += amount
        points.append(BalancePoint(when, identifier, balance))
    minimum = min(point.balance for point in points)
    return Simulation(tuple(points), minimum, minimum >= timeline.minimum_balance)
