"""Independent structural checks on serialized output; NOT a safety forecast."""

import csv
import re
from datetime import date
from decimal import Decimal
from pathlib import Path

from .domain import OUTPUT_COLUMNS, Method, Request, Status


class ValidationError(ValueError):
    pass


def _amount(text: str) -> Decimal:
    if not re.fullmatch(r"\d+(?:\.\d+)?", text):
        raise ValidationError(f"Invalid output monetary format: {text!r}")
    return Decimal(text)


def _date(text: str) -> date:
    try:
        parsed = date.fromisoformat(text)
    except ValueError as exc:
        raise ValidationError(f"Invalid output date: {text!r}") from exc
    if parsed.isoformat() != text:
        raise ValidationError(f"Output date must be YYYY-MM-DD: {text!r}")
    return parsed


def validate_row(row: dict[str, str], request: Request) -> None:
    if tuple(row) != OUTPUT_COLUMNS or any(v is None for v in row.values()):
        raise ValidationError("Output fields do not match required schema")
    for key in OUTPUT_COLUMNS:
        if key != "earliest_date_for_full_payment" and not row[key].strip():
            raise ValidationError(f"Missing required output: {key}")
    if row["request_id"] != request.request_id:
        raise ValidationError("Prediction/request ID mismatch")
    safe = _amount(row["amount_safe_to_pay"])
    if safe > request.requested_amount:
        raise ValidationError("Safe amount exceeds request")
    try:
        status = Status(row["affordability_status"])
        method = Method(row["recommended_payment_method"])
    except ValueError as exc:
        raise ValidationError("Invalid status or method") from exc
    earliest = _date(row["earliest_date_for_full_payment"]) if row["earliest_date_for_full_payment"] else None
    if earliest and earliest < request.request_date:
        raise ValidationError("Earliest full payment precedes request")
    payments = []
    if row["payment_plan"] != "none":
        for item in row["payment_plan"].split("|"):
            pieces = item.split(":")
            if len(pieces) != 2:
                raise ValidationError("Malformed payment entry")
            when, amount = _date(pieces[0]), _amount(pieces[1])
            if amount <= 0 or not request.request_date <= when <= request.desired_completion_date:
                raise ValidationError("Payment amount/date outside request bounds")
            payments.append((when, amount))
    if any(a[0] > b[0] for a, b in zip(payments, payments[1:])):
        raise ValidationError("Payment plan is not chronological")
    changes = row["spending_changes_needed"]
    targets = set()
    if changes != "none":
        actions = changes.split("|")
        if len(actions) > 3:
            raise ValidationError("More than three spending changes")
        for action in actions:
            parts = action.split(":")
            if len(parts) < 2 or not parts[1] or parts[1] in targets:
                raise ValidationError("Missing or duplicate spending target")
            targets.add(parts[1])
            if parts[0] == "reduce_to" and len(parts) == 3:
                _amount(parts[2])
            elif not (parts[0] == "stop" and len(parts) == 2):
                raise ValidationError("Malformed spending change")
    if method == Method.NO:
        if status != Status.NO or payments or changes != "none":
            raise ValidationError("Inconsistent not-recommended output")
    elif not payments:
        raise ValidationError("Recommended payment requires a plan")
    if status == Status.NO and method != Method.NO:
        raise ValidationError("Not affordable cannot recommend payment")
    if status == Status.NOW:
        if method != Method.FULL or safe != request.requested_amount or earliest != request.request_date or changes != "none" or payments != [(request.request_date, request.requested_amount)]:
            raise ValidationError("Inconsistent affordable-now output")
    if method in {Method.FULL, Method.WAIT}:
        if len(payments) != 1 or payments[0][1] != request.requested_amount:
            raise ValidationError("Full payment must pay the requested total once")
    if method == Method.FULL and status not in {Status.NOW, Status.PLAN}:
        raise ValidationError("Full payment has inconsistent status")
    if method == Method.FULL and status == Status.PLAN and changes == "none":
        raise ValidationError("Full payment with plan requires spending changes")
    if method == Method.WAIT or status == Status.LATER:
        if method != Method.WAIT or status != Status.LATER or earliest is None or earliest <= request.request_date or payments != [(earliest, request.requested_amount)] or changes != "none":
            raise ValidationError("Inconsistent wait output")
    if method == Method.PARTIAL:
        if status != Status.PLAN or not request.allows_partial_payment or not 0 < safe < request.requested_amount or earliest is None or earliest <= request.request_date or payments != [(request.request_date, safe), (earliest, request.requested_amount - safe)]:
            raise ValidationError("Inconsistent two-payment partial plan")
    if method == Method.INSTALLMENTS:
        if status != Status.PLAN or len(payments) < 2 or sum(p[1] for p in payments) < request.requested_amount:
            raise ValidationError("Inconsistent installment structure")


def validate_output(path: Path, requests: tuple[Request, ...]) -> None:
    by_id = {r.request_id: r for r in requests}
    if len(by_id) != len(requests):
        raise ValidationError("Duplicate input requests")
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != OUTPUT_COLUMNS:
            raise ValidationError("Output header must match exact columns and order")
        seen = set()
        for row in reader:
            rid = row.get("request_id")
            if rid not in by_id or rid in seen:
                raise ValidationError("Unknown or duplicate output request")
            validate_row(row, by_id[rid])
            seen.add(rid)
        if seen != set(by_id):
            raise ValidationError("Missing output requests")
