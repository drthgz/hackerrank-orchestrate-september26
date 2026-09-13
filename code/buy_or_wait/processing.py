"""Limited decision stage. Never interprets records or infers recurrence."""

from .domain import FinancialContext, Method, Payment, Prediction, Status, UnsupportedCase
from .forecast import ForecastTimeline, simulate


def decide(context: FinancialContext, timeline: ForecastTimeline) -> Prediction:
    request = context.request
    if Method.FULL not in context.profile.methods:
        raise UnsupportedCase("Slice only selects an eligible immediate full payment")
    options = [o for o in context.options if o.method == Method.FULL and o.first_payment_date == request.request_date and o.number_of_payments == 1 and o.total == request.requested_amount and o.financing_fee == 0]
    if not options:
        raise UnsupportedCase("No matching immediate fee-free full-payment option")
    payment = Payment(request.request_date, request.requested_amount)
    result = simulate(timeline, (payment,))
    if not result.safe:
        raise UnsupportedCase("Immediate full payment is unsafe; later/partial/installment planning is not implemented")
    # Paying the entire capped request proves amount_safe_to_pay equals the cap.
    # No need to implement general capacity/date search for this sufficient case.
    return Prediction(request.request_id, request.requested_amount, Status.NOW, Method.FULL,
                      (payment,), request.request_date, (),
                      f"Provisional {timeline.policy.version}: pay {context.profile.currency} "
                      f"{request.requested_amount} today; projected minimum balance "
                      f"{result.minimum_balance} remains at least {context.profile.minimum} "
                      "over the request-relative 90-day horizon, without spending changes.")
