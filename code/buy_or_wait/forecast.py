"""Provisional vertical-slice policy, replaceable after sample evaluation.

No CSV knowledge, evidence interpretation, label access, or payment selection.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from statistics import median

from .domain import CashKind, Event, FinancialContext, Payment, UnsupportedCase
from .reconciliation import ResolvedContext, reconcile, stream_key
from .fx import to_home


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
    version: str = "deterministic-core-v2"
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


def _next_month(value: date) -> date:
    year = value.year + (value.month == 12)
    month = value.month % 12 + 1
    return date(year, month, value.day)


def infer_occurrences(history: tuple[Event, ...], start: date, end: date,
                      policy: ForecastPolicy) -> tuple[tuple[date, Decimal], ...]:
    """Strict patterns only; uncertainty is an error, never absence of expense."""
    if len(history) < policy.min_occurrences:
        raise UnsupportedCase("Recurrence needs at least three historical occurrences")
    if len({stream_key(e) for e in history}) != 1:
        raise UnsupportedCase("Mixed financial streams")
    ordered = sorted(history, key=lambda e: (e.settlement_date or date.min, e.event_id))
    if any(e.amount is None or e.amount <= 0 or e.settlement_date is None for e in ordered):
        raise UnsupportedCase("Recurrence has missing/zero amount or date")
    amounts = [e.amount for e in ordered]
    center = median(amounts)
    if any(abs(amount - center) > center * policy.max_relative_amount_deviation for amount in amounts):
        raise UnsupportedCase("Amounts are too variable for provisional recurrence")
    dates = [e.settlement_date for e in ordered]
    if len(set(dates)) != len(dates):
        raise UnsupportedCase("Multiple same-day records make stream identity ambiguous")
    projected_amount = max(amounts) if ordered[0].direction == "debit" else min(amounts)
    by_month = defaultdict(set)
    for when in dates:
        by_month[when.year * 12 + when.month].add(when.day)
    months = sorted(by_month)
    slots = by_month[months[0]]
    monthly = (
        len(months) >= policy.min_months
        and 1 <= len(slots) <= policy.max_monthly_slots
        and all(day <= policy.last_supported_monthly_day for day in slots)
        and all(b - a == 1 for a, b in zip(months, months[1:]))
        and all(days == slots for days in by_month.values())
    )
    future = []
    if monthly:
        for slot in sorted(slots):
            when = _next_month(dates[-1].replace(day=slot))
            if when < start:
                raise UnsupportedCase("Historical monthly stream is stale")
            while when <= end:
                future.append((when, projected_amount))
                when = _next_month(when)
    else:
        gaps = {(b - a).days for a, b in zip(dates, dates[1:])}
        if len(gaps) != 1 or next(iter(gaps)) not in policy.fixed_intervals:
            raise UnsupportedCase("Ambiguous or unsupported recurrence cadence")
        interval = timedelta(days=next(iter(gaps)))
        when = dates[-1] + interval
        if when < start:
            raise UnsupportedCase("Historical fixed-interval stream is stale")
        while when <= end:
            future.append((when, projected_amount))
            when += interval
    return tuple(sorted(future))


def build_forecast(context: FinancialContext | ResolvedContext,
                   policy: ForecastPolicy = ForecastPolicy()) -> ForecastTimeline:
    # Compatibility for direct callers; the application invokes reconciliation
    # as its own stage and passes a ResolvedContext. No lifecycle logic lives here.
    resolved = context if isinstance(context, ResolvedContext) else reconcile(context)
    context = resolved.context
    if context.evidence:
        raise UnsupportedCase("Uninterpreted messages/images require later extraction")
    if any(e.amount is None for e in resolved.events):
        raise UnsupportedCase("Missing financial amount remains unresolved")
    start = context.request.request_date
    end = start + timedelta(days=policy.horizon_days)
    history = defaultdict(list)
    explicit = {}
    entries = []
    terminated = {end.stream: end for end in resolved.stream_ends}
    treatments = {item.event_id: item for item in resolved.treatments}
    for event in resolved.events:
        when = event.settlement_date
        if when is None:
            raise UnsupportedCase("Active cash event is missing settlement date")
        if event.status == "settled" and when < start:
            if treatments[event.event_id].recurrence_eligible:
                history[stream_key(event)].append(event)
            continue
        if when < start and event.status != "pending":
            raise UnsupportedCase("Overdue scheduled cash event needs reconciliation")
        if event.status == "settled" and when == start:
            raise UnsupportedCase("Same-day settled event snapshot is unresolved")
        if when > end and event.status != "pending":
            continue
        key = (stream_key(event), when)
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
    for key, records in sorted(history.items()):
        if key in terminated:
            continue  # Historical final payroll is cash history, not future income.
        if len({e.currency for e in records}) != 1:
            raise UnsupportedCase("Mixed-currency stream needs source reconciliation")
        try:
            occurrences = infer_occurrences(tuple(records), start, end, policy)
        except UnsupportedCase as exc:
            raise UnsupportedCase(f"Stream {key}: {exc}") from exc
        if key[2] == "credit" and key[:2] != ("income", "salary"):
            raise UnsupportedCase("Only repeated structured salary income is supported")
        for when, amount in occurrences:
            if (key, when) in explicit:
                continue
            sign = Decimal("-1") if key[2] == "debit" else Decimal("1")
            converted, rate_sources = to_home(amount, records[0].currency, context.profile.currency, when, context.rates)
            entries.append(ForecastEntry(when, sign * converted, f"inferred:{':'.join(key)}:{when}", tuple(sorted(e.source.source_id for e in records)) + rate_sources, "recurrence"))
    for release in resolved.reservation_releases:
        if start <= release.date <= end:
            converted, rate_sources = to_home(release.amount, release.currency, context.profile.currency, release.date, context.rates)
            entries.append(ForecastEntry(release.date, converted, f"reservation-release:{release.source_ids[-1]}", release.source_ids + rate_sources, "reservation_release"))
    return ForecastTimeline(start, end, context.profile.balance, context.profile.minimum,
                            tuple(sorted(entries, key=lambda e: (e.date, e.entry_id))), policy)


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
