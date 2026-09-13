"""Deterministic semantic comparisons, independent of decision generation."""

import re
from datetime import date
from decimal import Decimal

from buy_or_wait.domain import OUTPUT_COLUMNS

# Identifier and explanation are diagnostics, not financial accuracy fields.
STRUCTURED_FIELDS = OUTPUT_COLUMNS[1:-1]


def _money(value: str) -> Decimal:
    value = value.strip()
    if not re.fullmatch(r"\d+(?:\.\d+)?", value):
        raise ValueError("Invalid nonnegative monetary representation")
    return Decimal(value)


def _date(value: str) -> date | None:
    value = value.strip()
    if not value:
        return None
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError("Date must use YYYY-MM-DD")
    return parsed


def _plan(value: str) -> tuple:
    if value.strip() == "none":
        return ()
    payments = []
    for part in value.split("|"):
        when, amount = part.strip().split(":")
        parsed_date, parsed_amount = _date(when), _money(amount)
        if parsed_date is None or parsed_amount <= 0:
            raise ValueError("Missing payment date or nonpositive payment")
        payments.append((parsed_date, parsed_amount))
    if any(a[0] > b[0] for a, b in zip(payments, payments[1:])):
        raise ValueError("Nonchronological plan")
    # Preserve payment count; never combine separate same-day installments.
    return tuple(payments)


def _changes(value: str) -> tuple:
    if value.strip() == "none":
        return ()
    changes = []
    targets = set()
    for part in value.split("|"):
        pieces = [p.strip() for p in part.split(":")]
        if len(pieces) < 2 or not pieces[1] or pieces[1] in targets:
            raise ValueError("Invalid/duplicate spending target")
        targets.add(pieces[1])
        if pieces[0] == "stop" and len(pieces) == 2:
            changes.append((pieces[0], pieces[1], None))
        elif pieces[0] == "reduce_to" and len(pieces) == 3:
            changes.append((pieces[0], pieces[1], _money(pieces[2])))
        else:
            raise ValueError("Malformed spending change")
    if len(changes) > 3:
        raise ValueError("Too many spending changes")
    return tuple(sorted(changes))


def compare_field(field: str, expected: str, actual: str) -> dict:
    result = {"field": field, "expected": expected, "actual": actual, "match": False, "details": {}}
    if field == "decision_explanation":
        result["match"] = expected == actual
        result["details"] = {"diagnostic_only": True, "consistency": "not_assessed"}
        return result
    try:
        if field == "amount_safe_to_pay":
            left, right = _money(expected), _money(actual)
            if left != right:
                result["details"] = {"absolute_error": format(abs(right - left), "f")}
        elif field == "earliest_date_for_full_payment":
            left, right = _date(expected), _date(actual)
            if left != right:
                result["details"] = {"day_difference_actual_minus_expected": (right - left).days if right and left else None,
                                     "presence_mismatch": (left is None) != (right is None)}
        elif field == "payment_plan":
            left, right = _plan(expected), _plan(actual)
            if left != right:
                result["details"] = {"expected_payment_count": len(left), "actual_payment_count": len(right),
                                     "different_payment_indexes": [i for i in range(max(len(left), len(right))) if i >= len(left) or i >= len(right) or left[i] != right[i]]}
        elif field == "spending_changes_needed":
            left, right = _changes(expected), _changes(actual)
        else:
            left, right = expected.strip(), actual.strip()
        result["match"] = left == right
    except (ValueError, ArithmeticError) as exc:
        result["details"] = {"comparison_error": str(exc)}
    return result


def compare_prediction(expected: dict[str, str], actual: dict[str, str]) -> list[dict]:
    return [compare_field(field, expected[field], actual[field]) for field in OUTPUT_COLUMNS]
