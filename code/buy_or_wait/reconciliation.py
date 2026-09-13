"""Deterministic financial-event semantics, separate from recurrence inference."""

from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal

from .domain import CashKind, DataError, Event, FinancialContext, UnsupportedCase


def stream_key(event: Event) -> tuple[str, str, str]:
    return event.event_type, event.category, event.direction


@dataclass(frozen=True)
class StreamEnd:
    stream: tuple[str, str, str]
    date: date
    source_ids: tuple[str, ...]
    reason: str


def ended_streams(context: FinancialContext) -> tuple[StreamEnd, ...]:
    """Narrow deterministic parser for an explicit terminal payroll label.

    No substring/fuzzy matching, no assumptions about other description wording,
    and no employer identity inferred from a category when later income conflicts.
    """
    ends = []
    for event in context.events:
        if (stream_key(event) == ("income", "salary", "credit")
                and event.status == "settled"
                and event.description.strip().casefold() == "final employer payroll"):
            if event.settlement_date is None:
                raise UnsupportedCase("Terminal payroll lacks a settlement date")
            ends.append(StreamEnd(stream_key(event), event.settlement_date,
                                  (event.source.source_id,), "Explicit final employer payroll ends this stream"))
    return tuple(ends)


@dataclass(frozen=True)
class EventTreatment:
    event_id: str
    source_ids: tuple[str, ...]
    cash_kind: CashKind
    participates: bool
    cash_affecting: bool
    recurrence_eligible: bool
    interpretation: str
    reason: str


@dataclass(frozen=True)
class ResolvedContext:
    context: FinancialContext
    events: tuple[Event, ...]
    treatments: tuple[EventTreatment, ...]
    stream_ends: tuple[StreamEnd, ...]
    reservation_releases: tuple["ReservationRelease", ...]


@dataclass(frozen=True)
class ReservationRelease:
    date: date
    amount: Decimal
    source_ids: tuple[str, ...]
    currency: str


def reconcile(context: FinancialContext) -> ResolvedContext:
    """Resolve only relationships justified by supplied type/status/direction.

    Links alone never imply duplicates. Unknown relationships remain unsupported.
    Original records are immutable; effective reservations may replace a future
    settlement representation, with all ancestor IDs retained in treatments.
    """
    by_id = {e.event_id: e for e in context.events}
    if len(by_id) != len(context.events):
        raise DataError("Duplicate event IDs in reconciliation")
    ancestors = {}

    def lineage(event_id, visiting=()):
        if event_id in visiting:
            raise DataError("Cyclic lifecycle references")
        if event_id not in by_id:
            raise DataError("Missing lifecycle target")
        if event_id not in ancestors:
            event = by_id[event_id]
            ancestors[event_id] = (lineage(event.linked_event_id, visiting + (event_id,)) if event.linked_event_id else ()) + (event.source.source_id,)
        return ancestors[event_id]

    for event in context.events:
        lineage(event.event_id)
    suppressed = {}
    effective = dict(by_id)
    relations = {}
    replacement_children = {}
    releases = []
    for event in sorted(context.events, key=lambda e: (len(ancestors[e.event_id]), e.event_id)):
        if not event.linked_event_id:
            continue
        previous = by_id[event.linked_event_id]
        if previous.event_date > event.event_date:
            raise DataError("Lifecycle successor precedes its source event")
        same_cash = (stream_key(previous) == stream_key(event) and previous.currency == event.currency
                     and previous.cash_kind == CashKind.CASH)
        replacement = same_cash and (
            (previous.status in {"cancelled", "failed"} and event.status in {"scheduled", "settled", "pending"})
            or (previous.status == "pending" and event.status == "settled"))
        if replacement:
            if previous.event_id in replacement_children:
                raise UnsupportedCase("Multiple replacement successors need reconciliation")
            replacement_children[previous.event_id] = event.event_id
            suppressed[previous.event_id] = f"Replaced by {event.event_id}; retain successor once"
            relations[event.event_id] = "replacement"
            if previous.status == "pending" and event.direction == "debit" and event.settlement_date is not None and event.settlement_date >= context.request.request_date:
                if previous.amount is None or event.amount is None:
                    raise UnsupportedCase("Replacement reservation has unresolved amount")
                reserve = max(previous.amount, event.amount)
                effective[event.event_id] = replace(event, status="pending", amount=reserve)
                if reserve > event.amount:
                    releases.append(ReservationRelease(event.settlement_date, reserve - event.amount, ancestors[event.event_id], event.currency))
                relations[event.event_id] = "replacement_reserved"
        elif (event.event_type == "refund" and event.direction == "credit"
              and previous.direction == "debit" and previous.status == "settled"):
            relations[event.event_id] = "refund_or_reversal"
            # The original debit remains a distinct movement, even for full refunds.
        elif (event.event_type in {"investment_valuation", "investment_sale"}
              and previous.event_type in {"investment_purchase", "investment_valuation"}):
            relations[event.event_id] = "investment_lifecycle"
        elif same_cash and previous.status == "settled" and event.status == "pending":
            relations[event.event_id] = "unconfirmed_duplicate_reserved"
        else:
            raise UnsupportedCase(f"Unresolved lifecycle {previous.event_id} -> {event.event_id}")
    active, treatments = [], []
    for raw in sorted(context.events, key=lambda e: e.event_id):
        event = effective[raw.event_id]
        relation = relations.get(raw.event_id)
        if raw.event_id in suppressed:
            participation, cash, meaning, reason = False, False, "replaced", suppressed[raw.event_id]
        elif event.cash_kind == CashKind.INFORMATIONAL:
            participation, cash, meaning, reason = False, False, "informational", "Non-cash valuation; no spendable cash impact"
        elif event.status in {"failed", "cancelled"}:
            participation, cash, meaning, reason = False, False, event.status, "Inactive transaction has no cash impact"
        elif event.direction == "credit" and event.status != "settled" and not (event.category == "salary" and event.status == "scheduled"):
            participation, cash, meaning, reason = True, False, "unsettled_credit", "No cash until settled; retain record to suppress duplicate inference"
        elif event.direction == "debit" and event.status == "pending":
            participation, cash, meaning, reason = True, True, "reserved", "Reserve once at request date; do not spend this cash"
        else:
            participation, cash, meaning, reason = True, True, event.status, "Distinct cash movement; past settlements already reflected in opening balance"
        if relation:
            reason += f"; relationship={relation}"
        recurring = participation and event.event_type not in {"refund", "investment_sale"}
        if not recurring and participation:
            reason += "; compensating/asset-sale proceeds are not recurring income"
        treatments.append(EventTreatment(raw.event_id, ancestors[raw.event_id], event.cash_kind, participation, cash, recurring, meaning, reason))
        if participation:
            active.append(event)
    return ResolvedContext(context, tuple(active), tuple(treatments), ended_streams(replace(context, events=tuple(active))), tuple(releases))
