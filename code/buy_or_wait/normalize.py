"""Convert CSV representations into source-independent typed financial facts."""

import re
from datetime import date
from decimal import Decimal

from .domain import (DataError, Event, Evidence, FinancialContext, FxRate, Method,
                     PaymentOption, Profile, Request, Source)
from .loading import RawContext


def money(value: str) -> Decimal:
    if not re.fullmatch(r"\d+(?:\.\d+)?", value):
        raise DataError(f"Invalid nonnegative decimal: {value!r}")
    return Decimal(value)


def day(value: str) -> date:
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise DataError(f"Invalid date: {value!r}") from exc
    if parsed.isoformat() != value:
        raise DataError(f"Date must be YYYY-MM-DD: {value!r}")
    return parsed


def positive_integer(value: str) -> int:
    if not re.fullmatch(r"[1-9]\d*", value):
        raise DataError(f"Invalid positive integer: {value!r}")
    return int(value)


def method(value: str) -> Method:
    try:
        return Method(value)
    except ValueError as exc:
        raise DataError(f"Invalid payment method: {value}") from exc


def normalize(raw: RawContext) -> FinancialContext:
    r, p = raw.request, raw.profile
    if r["allows_partial_payment"] not in ("true", "false"):
        raise DataError("allows_partial_payment must be true or false")
    request = Request(r["request_id"], r["user_id"], day(r["request_date"]), r["request_type"], money(r["requested_amount"]), day(r["desired_completion_date"]), r["allows_partial_payment"] == "true", r["request_text"])
    if request.requested_amount <= 0 or request.desired_completion_date < request.request_date:
        raise DataError("Invalid request amount or deadline")
    categories = lambda key: frozenset(filter(None, p[key].split("|")))
    methods = frozenset(method(v) for v in p["payment_methods_user_will_consider"].split("|"))
    if not methods <= {Method.FULL, Method.PARTIAL, Method.INSTALLMENTS}:
        raise DataError("Profile contains invalid immediate payment methods")
    profile = Profile(p["user_id"], p["home_currency"], money(p["current_available_balance"]), money(p["minimum_balance_to_keep"]), methods, categories("expense_categories_to_protect"), categories("expense_categories_user_is_willing_to_reduce"), categories("expense_categories_user_is_willing_to_stop"), positive_integer(p["max_installment_months"]) if p["max_installment_months"] else None)
    events = []
    for e in raw.events:
        if e["status"] not in {"settled", "pending", "scheduled", "failed", "cancelled", "unrealized"} or e["direction"] not in {"debit", "credit"}:
            raise DataError(f"{e['event_id']}: invalid cash state/direction")
        if not e["currency"] or not e["category"]:
            raise DataError(f"{e['event_id']}: missing currency/category")
        if not e["settlement_date"] and e["status"] != "unrealized":
            raise DataError(f"{e['event_id']}: missing cash settlement date")
        events.append(Event(e["event_id"], e["category"], e["event_type"], e["description"], money(e["amount"]) if e["amount"] else None, e["currency"], e["direction"], day(e["event_date"]), day(e["settlement_date"]) if e["settlement_date"] else None, e["status"], e["linked_event_id"] or None, e["flexibility"], money(e["minimum_allowed_amount"]) if e["minimum_allowed_amount"] else None, Source("financial_event", e["event_id"])))
    options = []
    for o in raw.options:
        option = PaymentOption(o["payment_option_id"], method(o["payment_method"]), money(o["payment_amount"]), positive_integer(o["number_of_payments"]), day(o["first_payment_date"]), positive_integer(o["payment_frequency_days"]) if o["payment_frequency_days"] else None, money(o["financing_fee"]), money(o["total_payable_amount"]))
        if option.method not in {Method.FULL, Method.INSTALLMENTS} or option.payment_amount <= 0 or option.total != option.payment_amount * option.number_of_payments:
            raise DataError(f"{option.option_id}: inconsistent payment schedule")
        if option.first_payment_date < request.request_date or (option.number_of_payments > 1 and option.frequency_days is None):
            raise DataError(f"{option.option_id}: invalid schedule dates")
        if option.total != request.requested_amount + option.financing_fee:
            raise DataError(f"{option.option_id}: inconsistent financing fee")
        options.append(option)
    evidence = tuple(Evidence(Source(kind, e[key]), e["request_id"] or None, e["related_event_id"] or None) for kind, key, records in (("message", "message_id", raw.messages), ("image", "image_id", raw.images)) for e in records)
    rates = tuple(FxRate(day(f["rate_date"]), f["from_currency"], f["to_currency"], money(f["rate"])) for f in raw.rates)
    if any(f.rate <= 0 for f in rates):
        raise DataError("FX rate must be positive")
    keys = {(f.settlement_date, f.from_currency, f.to_currency) for f in rates}
    for e in events:
        if e.currency != profile.currency and e.status in {"settled", "pending", "scheduled"} and (e.settlement_date, e.currency, profile.currency) not in keys:
            raise DataError(f"{e.event_id}: missing settlement-date FX rate")
    return FinancialContext(request, profile, tuple(events), tuple(options), evidence, rates)
