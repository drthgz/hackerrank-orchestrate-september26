"""Deterministic candidate generation, simulation, eligibility, and ranking."""

from dataclasses import dataclass, replace
from datetime import date, timedelta
from decimal import Decimal, ROUND_DOWN
from itertools import combinations

from .domain import (FinancialContext, Method, Payment, Prediction, SpendingChange,
                     Status)
from .forecast import ForecastEntry, ForecastTimeline, Simulation, simulate
from .fx import to_home
from .streams import Continuation

CENT = Decimal("0.01")


@dataclass(frozen=True)
class Candidate:
    method: Method
    payments: tuple[Payment, ...]
    changes: tuple[SpendingChange, ...] = ()
    option_id: str = ""
    total_paid: Decimal = Decimal("0")


@dataclass(frozen=True)
class CandidateEvaluation:
    candidate: Candidate
    eligible: bool
    rejection_reason: str | None
    minimum_projected_balance: Decimal | None
    completion_date: date | None
    rank: int | None = None


@dataclass(frozen=True)
class PlanningResult:
    prediction: Prediction
    amount_safe_today: Decimal
    earliest_safe_full_date: date | None
    evaluations: tuple[CandidateEvaluation, ...]


def safe_capacity(timeline: ForecastTimeline, cap: Decimal) -> Decimal:
    """Largest cent-denominated payment today proven safe by simulation."""
    upper = max(Decimal("0"), cap).quantize(CENT, rounding=ROUND_DOWN)
    low, high = 0, int((upper / CENT).to_integral_value(rounding=ROUND_DOWN))
    while low < high:
        middle = (low + high + 1) // 2
        amount = CENT * middle
        if simulate(timeline, (Payment(timeline.start, amount),)).safe:
            low = middle
        else:
            high = middle - 1
    return CENT * low


def earliest_safe_full_date(timeline: ForecastTimeline, amount: Decimal) -> date | None:
    current = timeline.start
    while current <= timeline.end:
        if simulate(timeline, (Payment(current, amount),)).safe:
            return current
        current += timedelta(days=1)
    return None


def _option_schedule(option) -> tuple[Payment, ...]:
    if option.number_of_payments == 1:
        return (Payment(option.first_payment_date, option.payment_amount),)
    return tuple(Payment(option.first_payment_date + timedelta(days=option.frequency_days * index),
                         option.payment_amount)
                 for index in range(option.number_of_payments))


def _base_candidates(context: FinancialContext, safe: Decimal,
                     earliest: date | None) -> tuple[Candidate, ...]:
    request, profile = context.request, context.profile
    candidates = []
    full_options = [option for option in context.options
                    if option.method == Method.FULL and option.number_of_payments == 1
                    and option.first_payment_date == request.request_date
                    and option.total == request.requested_amount]
    if Method.FULL in profile.methods and full_options:
        candidates.append(Candidate(Method.FULL,
                                    (Payment(request.request_date, request.requested_amount),),
                                    total_paid=request.requested_amount))
    if (Method.FULL in profile.methods and earliest is not None
            and earliest > request.request_date):
        candidates.append(Candidate(Method.WAIT, (Payment(earliest, request.requested_amount),),
                                    total_paid=request.requested_amount))
    if (request.allows_partial_payment and Method.PARTIAL in profile.methods
            and Decimal("0") < safe < request.requested_amount and earliest is not None):
        candidates.append(Candidate(Method.PARTIAL,
                                    (Payment(request.request_date, safe),
                                     Payment(earliest, request.requested_amount - safe)),
                                    total_paid=request.requested_amount))
    if Method.INSTALLMENTS in profile.methods:
        for option in context.options:
            if option.method != Method.INSTALLMENTS:
                continue
            candidates.append(Candidate(Method.INSTALLMENTS, _option_schedule(option),
                                        option_id=option.option_id, total_paid=option.total))
    return tuple(candidates)


def _eligible_change_actions(context: FinancialContext,
                             timeline: ForecastTimeline) -> tuple[SpendingChange, ...]:
    by_id = {event.event_id: event for event in context.events}
    actions = []
    for stream in timeline.streams:
        if (stream.continuation != Continuation.CONTINUING
                or stream.identity.direction != "debit" or not stream.source_event_ids):
            continue
        events = [by_id[source] for source in stream.source_event_ids if source in by_id]
        if not events:
            continue
        target = max(events, key=lambda event: (event.settlement_date or date.min, event.event_id))
        if target.category in context.profile.protected:
            continue
        if (target.flexibility in {"stoppable", "reducible_or_stoppable"}
                and target.category in context.profile.stop_categories):
            actions.append(SpendingChange("stop", target.event_id))
        if (target.flexibility in {"reducible", "reducible_or_stoppable"}
                and target.category in context.profile.reduce_categories
                and target.minimum_allowed_amount is not None
                and target.amount is not None
                and Decimal("0") <= target.minimum_allowed_amount < target.amount):
            actions.append(SpendingChange("reduce_to", target.event_id,
                                          target.minimum_allowed_amount))
    return tuple(sorted(actions, key=lambda action: (action.event_id, action.action)))


def _timeline_with_changes(context: FinancialContext, timeline: ForecastTimeline,
                           changes: tuple[SpendingChange, ...]) -> ForecastTimeline:
    by_id = {event.event_id: event for event in context.events}
    entries = list(timeline.entries)
    for change in changes:
        event = by_id[change.event_id]
        updated = []
        for entry in entries:
            affected = (change.event_id in entry.source_ids
                        and (entry.basis.startswith("recurrence:")
                             or entry.basis.startswith("behavior_contingency:")))
            if not affected:
                updated.append(entry)
                continue
            if change.action == "stop":
                continue
            amount, rate_sources = to_home(change.new_amount, event.currency,
                                           context.profile.currency, entry.date, context.rates)
            updated.append(replace(entry, amount=-amount,
                                   source_ids=entry.source_ids + rate_sources,
                                   basis=f"spending_change:{change.action}:{change.event_id}"))
        entries = updated
    return replace(timeline, entries=tuple(sorted(entries, key=lambda item: (item.date, item.entry_id))))


def _evaluate(context: FinancialContext, timeline: ForecastTimeline,
              candidate: Candidate) -> CandidateEvaluation:
    request = context.request
    completion = candidate.payments[-1].date if candidate.payments else None
    reason = None
    if not candidate.payments or sum(payment.amount for payment in candidate.payments) != candidate.total_paid:
        reason = "payment schedule does not complete candidate total"
    elif completion > request.desired_completion_date:
        reason = "completion is after desired completion date"
    elif candidate.method == Method.PARTIAL and len(candidate.payments) != 2:
        reason = "partial payment must contain exactly two payments"
    elif candidate.method == Method.INSTALLMENTS:
        option = next((item for item in context.options if item.option_id == candidate.option_id), None)
        if option is None or candidate.payments != _option_schedule(option):
            reason = "installment schedule does not match a supplied option"
        elif (context.profile.max_installment_months is None
              or option.number_of_payments > context.profile.max_installment_months):
            reason = "installment option exceeds user duration preference"
    if reason:
        return CandidateEvaluation(candidate, False, reason, None, completion)
    changed_timeline = _timeline_with_changes(context, timeline, candidate.changes)
    simulation = simulate(changed_timeline, candidate.payments)
    if not simulation.safe:
        return CandidateEvaluation(candidate, False, "minimum-balance simulation failed",
                                   simulation.minimum_balance, completion)
    return CandidateEvaluation(candidate, True, None, simulation.minimum_balance, completion)


def _rank_key(item: CandidateEvaluation):
    candidate = item.candidate
    method_order = {Method.FULL: 0, Method.PARTIAL: 1, Method.INSTALLMENTS: 2,
                    Method.WAIT: 3}
    return (bool(candidate.changes), len(candidate.changes), candidate.total_paid,
            candidate.payments[0].date, len(candidate.payments), candidate.option_id,
            method_order[candidate.method])


def plan(context: FinancialContext, timeline: ForecastTimeline) -> PlanningResult:
    request = context.request
    safe = safe_capacity(timeline, request.requested_amount)
    earliest = earliest_safe_full_date(timeline, request.requested_amount)
    candidates = list(_base_candidates(context, safe, earliest))

    # Spending changes are considered only for completing the full request now;
    # combinations are enumerated by size to find the minimum necessary set.
    actions = _eligible_change_actions(context, timeline)
    if Method.FULL in context.profile.methods:
        for count in range(1, min(3, len(actions)) + 1):
            for selected in combinations(actions, count):
                if len({change.event_id for change in selected}) != count:
                    continue
                candidates.append(Candidate(Method.FULL,
                                            (Payment(request.request_date, request.requested_amount),),
                                            selected, total_paid=request.requested_amount))

    evaluations = [_evaluate(context, timeline, candidate) for candidate in candidates]
    valid = sorted((item for item in evaluations if item.eligible), key=_rank_key)
    ranked = {id(item): index + 1 for index, item in enumerate(valid)}
    evaluations = tuple(replace(item, rank=ranked.get(id(item))) for item in evaluations)

    if not valid:
        prediction = Prediction(request.request_id, safe, Status.NO, Method.NO, (), earliest, (),
                                f"No eligible payment strategy completes the request while preserving "
                                f"the {context.profile.currency} {context.profile.minimum} minimum.")
        return PlanningResult(prediction, safe, earliest, evaluations)

    selected = valid[0].candidate
    if selected.method == Method.FULL:
        status = Status.PLAN if selected.changes else Status.NOW
    elif selected.method == Method.WAIT:
        status = Status.LATER
    else:
        status = Status.PLAN
    minimum = valid[0].minimum_projected_balance
    explanation = (f"Use {selected.method.value} with {len(selected.payments)} payment(s); "
                   f"projected minimum balance {context.profile.currency} {minimum} remains at least "
                   f"{context.profile.minimum}.")
    prediction = Prediction(request.request_id, safe, status, selected.method,
                            selected.payments, earliest, selected.changes, explanation)
    return PlanningResult(prediction, safe, earliest, evaluations)
