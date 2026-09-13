"""Pure prediction-to-CSV serialization; validation is a separate component."""

import csv
from decimal import Decimal
from pathlib import Path

from .domain import OUTPUT_COLUMNS, Prediction


def decimal_text(value: Decimal) -> str:
    if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
        raise ValueError("Output money must be a finite nonnegative Decimal")
    return format(value, "f")


def prediction_row(prediction: Prediction) -> dict[str, str]:
    changes = []
    for change in prediction.spending_changes_needed:
        if change.action == "stop" and change.new_amount is None:
            changes.append(f"stop:{change.event_id}")
        elif change.action == "reduce_to" and change.new_amount is not None:
            changes.append(f"reduce_to:{change.event_id}:{decimal_text(change.new_amount)}")
        else:
            raise ValueError("Invalid spending change")
    return dict(zip(OUTPUT_COLUMNS, (
        prediction.request_id,
        decimal_text(prediction.amount_safe_to_pay),
        prediction.affordability_status.value,
        prediction.recommended_payment_method.value,
        "|".join(f"{p.date.isoformat()}:{decimal_text(p.amount)}" for p in prediction.payment_plan) or "none",
        prediction.earliest_date_for_full_payment.isoformat() if prediction.earliest_date_for_full_payment else "",
        "|".join(changes) or "none",
        prediction.decision_explanation,
    )))


def write_predictions(path: Path, predictions: tuple[Prediction, ...]) -> None:
    rows = [prediction_row(p) for p in predictions]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=OUTPUT_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
