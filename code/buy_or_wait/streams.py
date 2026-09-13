"""Deterministic stream identity, continuation, cadence, and amount policies."""

from calendar import monthrange
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from enum import Enum
from statistics import median

from .domain import Event, UnsupportedCase
from .reconciliation import ResolvedContext


class StreamMode(str, Enum):
    TRANSACTION = "transaction"
    SPENDING_BEHAVIOR = "spending_behavior"


class Continuation(str, Enum):
    CONTINUING = "continuing"
    TERMINATED = "terminated"
    SUPERSEDED = "superseded"
    ONE_TIME = "one_time"
    INSUFFICIENT = "insufficient_evidence"


@dataclass(frozen=True, order=True)
class StreamIdentity:
    mode: StreamMode
    event_type: str
    category: str
    direction: str
    currency: str
    label: str

    def diagnostic_id(self) -> str:
        return ":".join((self.mode.value, self.event_type, self.category,
                         self.direction, self.currency, self.label))


@dataclass(frozen=True)
class Cadence:
    name: str
    interval_days: int | None = None
    calendar_day: int | None = None
    tolerance_days: int = 0


@dataclass(frozen=True)
class ResolvedStream:
    identity: StreamIdentity
    source_event_ids: tuple[str, ...]
    observed_dates: tuple[date, ...]
    observed_intervals: tuple[int, ...]
    cadence: Cadence | None
    continuation: Continuation
    continuation_reason: str
    amount: Decimal | None
    amount_policy: str | None
    next_projected_dates: tuple[date, ...]


@dataclass(frozen=True)
class StreamPolicy:
    """Versioned deterministic interpretation; sample answers are not inputs."""

    version: str = "recurring-streams-v2"
    minimum_observations: int = 3
    fixed_intervals: tuple[int, ...] = (5, 7, 10, 14, 21, 28)
    interval_tolerance_days: int = 1
    monthly_day_tolerance: int = 2
    behavior_categories: tuple[str, ...] = ("groceries", "transport", "dining")


def identity_for(event: Event, policy: StreamPolicy = StreamPolicy()) -> StreamIdentity:
    behavior = (event.event_type == "expense" and event.direction == "debit"
                and event.category in policy.behavior_categories)
    mode = StreamMode.SPENDING_BEHAVIOR if behavior else StreamMode.TRANSACTION
    label = "category_behavior" if behavior else " ".join(event.description.casefold().split())
    return StreamIdentity(mode, event.event_type, event.category, event.direction,
                          event.currency, label)


def infer_cadence(dates: tuple[date, ...], policy: StreamPolicy = StreamPolicy()) -> Cadence:
    if len(dates) < policy.minimum_observations:
        raise UnsupportedCase("cadence: insufficient observations")
    ordered = tuple(sorted(dates))
    if len(set(ordered)) != len(ordered):
        raise UnsupportedCase("cadence: duplicate observation date")
    intervals = tuple((right - left).days for left, right in zip(ordered, ordered[1:]))
    candidates = [value for value in policy.fixed_intervals
                  if all(abs(gap - value) <= policy.interval_tolerance_days for gap in intervals)]
    if len(candidates) == 1:
        value = candidates[0]
        names = {7: "weekly", 14: "biweekly", 28: "four_weekly"}
        return Cadence(names.get(value, f"every_{value}_days"), value, None,
                       policy.interval_tolerance_days)

    month_indexes = tuple(value.year * 12 + value.month for value in ordered)
    days = tuple(value.day for value in ordered)
    if (all(right - left == 1 for left, right in zip(month_indexes, month_indexes[1:]))
            and max(days) - min(days) <= policy.monthly_day_tolerance):
        return Cadence("monthly", None, int(median(days)), policy.monthly_day_tolerance)
    raise UnsupportedCase(f"cadence: inconsistent intervals {intervals}")


def estimate_amount(events: tuple[Event, ...],
                    conservative_expense: bool = True) -> tuple[Decimal, str]:
    """Amount estimation is intentionally independent from cadence inference."""
    amounts = tuple(event.amount for event in events)
    if not amounts or any(value is None or value <= 0 for value in amounts):
        raise UnsupportedCase("amount: missing or non-positive observation")
    if events[0].direction == "debit":
        if conservative_expense:
            return max(amounts), "conservative_max_observed_expense"
        return sum(amounts) / len(amounts), "observed_mean_flexible_expense"
    if events[0].direction == "credit":
        return min(amounts), "conservative_min_observed_income"
    raise UnsupportedCase("amount: non-cash stream cannot project cash")


def _advance_month(value: date, target_day: int) -> date:
    year = value.year + (value.month == 12)
    month = value.month % 12 + 1
    return date(year, month, min(target_day, monthrange(year, month)[1]))


def project_dates(last: date, cadence: Cadence, start: date, end: date) -> tuple[date, ...]:
    future = []
    if cadence.interval_days is not None:
        current = last + timedelta(days=cadence.interval_days)
        while current < start:
            current += timedelta(days=cadence.interval_days)
        while current <= end:
            future.append(current)
            current += timedelta(days=cadence.interval_days)
    else:
        current = _advance_month(last, cadence.calendar_day)
        while current < start:
            current = _advance_month(current, cadence.calendar_day)
        while current <= end:
            future.append(current)
            current = _advance_month(current, cadence.calendar_day)
    return tuple(future)


def next_expected_date(last: date, cadence: Cadence) -> date:
    if cadence.interval_days is not None:
        return last + timedelta(days=cadence.interval_days)
    return _advance_month(last, cadence.calendar_day)


def _terminal_targets(groups: dict[StreamIdentity, list[Event]], terminal: Event) -> tuple[StreamIdentity, ...]:
    """Match an exact terminal payroll marker only when its source is unique."""
    matches = []
    for identity, events in groups.items():
        if (identity.event_type, identity.category, identity.direction, identity.currency) != (
                "income", "salary", "credit", terminal.currency):
            continue
        if any(event.amount == terminal.amount and event.event_id != terminal.event_id for event in events):
            matches.append(identity)
    return tuple(matches)


def resolve_streams(resolved: ResolvedContext, start: date, end: date,
                    policy: StreamPolicy = StreamPolicy()) -> tuple[ResolvedStream, ...]:
    treatments = {item.event_id: item for item in resolved.treatments}
    history = [event for event in resolved.events
               if event.status == "settled" and event.settlement_date is not None
               and event.settlement_date < start and treatments[event.event_id].recurrence_eligible]
    groups: dict[StreamIdentity, list[Event]] = {}
    salary = [event for event in history if event.event_type == "income"
              and event.category == "salary" and event.direction == "credit"]
    other = [event for event in history if event not in salary]
    for event in other:
        groups.setdefault(identity_for(event, policy), []).append(event)

    # Repeated structured payer/description labels are the strongest available
    # salary identity. Remaining variable labels may form independent calendar
    # slots; this captures contract/freelance income without merging two named
    # employers into one broad salary stream.
    by_label: dict[StreamIdentity, list[Event]] = {}
    for event in salary:
        by_label.setdefault(identity_for(event, policy), []).append(event)
    assigned = set()
    for identity, records in by_label.items():
        if len(records) >= policy.minimum_observations:
            groups[identity] = records
            assigned.update(event.event_id for event in records)
    by_slot: dict[tuple[str, int], list[Event]] = {}
    for event in salary:
        if event.event_id not in assigned:
            by_slot.setdefault((event.currency, event.settlement_date.day), []).append(event)
    for (currency, day), records in by_slot.items():
        label = f"calendar_slot:{day}"
        identity = StreamIdentity(StreamMode.TRANSACTION, "income", "salary",
                                  "credit", currency, label)
        groups[identity] = records

    terminated: set[StreamIdentity] = set()
    terminals = [event for event in history if event.event_type == "income"
                 and event.category == "salary"
                 and event.description.strip().casefold() == "final employer payroll"]
    for terminal in terminals:
        matches = _terminal_targets(groups, terminal)
        own = identity_for(terminal, policy)
        if len(matches) == 1:
            terminated.add(matches[0])
        elif len(matches) > 1:
            raise UnsupportedCase("continuation: terminal payroll matches multiple income streams")
        terminated.add(own)
        if any(event.event_id != terminal.event_id
               and event.event_type == "income" and event.category == "salary"
               and event.direction == "credit" and event.currency == terminal.currency
               and event.amount == terminal.amount and event.settlement_date is not None
               and event.settlement_date > terminal.settlement_date
               and event.status in {"settled", "scheduled", "pending"}
               for event in resolved.events):
            raise UnsupportedCase("continuation: income matching a terminated payroll stream appears later")

    streams = []
    for identity, records in sorted(groups.items()):
        ordered = tuple(sorted(records, key=lambda event: (event.settlement_date, event.event_id)))
        daily_amounts = None
        if identity.mode == StreamMode.SPENDING_BEHAVIOR:
            # Category behavior models daily outflow, so two genuine purchases
            # on one day are one cadence observation whose amount is their sum.
            # Raw event identity and provenance remain separate.
            totals: dict[date, Decimal] = {}
            for event in ordered:
                totals[event.settlement_date] = totals.get(event.settlement_date, Decimal("0")) + event.amount
            dates = tuple(sorted(totals))
            daily_amounts = tuple(totals[value] for value in dates)
        else:
            dates = tuple(event.settlement_date for event in ordered)
        intervals = tuple((right - left).days for left, right in zip(dates, dates[1:]))
        if identity in terminated:
            streams.append(ResolvedStream(identity, tuple(e.event_id for e in ordered), dates,
                                           intervals, None, Continuation.TERMINATED,
                                           "explicit final payroll marker", None, None, ()))
            continue
        if len(ordered) == 1:
            streams.append(ResolvedStream(identity, (ordered[0].event_id,), dates, (), None,
                                           Continuation.ONE_TIME,
                                           "one observation cannot establish recurrence", None, None, ()))
            continue
        try:
            cadence = infer_cadence(dates, policy)
        except UnsupportedCase as exc:
            streams.append(ResolvedStream(identity, tuple(e.event_id for e in ordered), dates,
                                           intervals, None, Continuation.INSUFFICIENT,
                                           str(exc), None, None, ()))
            continue
        protected = identity.category in resolved.context.profile.protected
        explicitly_flexible = all(event.flexibility in {
            "reducible", "stoppable", "reducible_or_stoppable"
        } for event in ordered)
        conservative_expense = protected or not explicitly_flexible
        if daily_amounts is not None:
            if conservative_expense:
                amount, amount_policy = (max(daily_amounts),
                                         "conservative_max_observed_daily_expense")
            else:
                amount, amount_policy = (sum(daily_amounts) / len(daily_amounts),
                                         "observed_mean_flexible_daily_expense")
        else:
            amount, amount_policy = estimate_amount(
                ordered, conservative_expense=conservative_expense)
        expected = next_expected_date(dates[-1], cadence)
        if expected + timedelta(days=cadence.tolerance_days) < start:
            streams.append(ResolvedStream(identity, tuple(e.event_id for e in ordered), dates,
                                           intervals, cadence, Continuation.INSUFFICIENT,
                                           f"continuation: expected occurrence {expected} is missing before request",
                                           amount, amount_policy, ()))
            continue
        projected = project_dates(dates[-1], cadence, start, end)
        streams.append(ResolvedStream(identity, tuple(e.event_id for e in ordered), dates,
                                       intervals, cadence, Continuation.CONTINUING,
                                       "supported repeated cadence with no cessation evidence",
                                       amount, amount_policy, projected))
    return tuple(streams)
