"""Read structured context only. The application never opens sample_requests.csv."""

import csv
from dataclasses import dataclass
from pathlib import Path

from .domain import DataError, REQUEST_COLUMNS

SCHEMAS = {
    "financial_profiles": ("user_id", "home_currency", "current_available_balance", "minimum_balance_to_keep", "financial_priorities", "expense_categories_to_protect", "expense_categories_user_is_willing_to_reduce", "expense_categories_user_is_willing_to_stop", "payment_methods_user_will_consider", "max_installment_months"),
    "financial_events": ("event_id", "user_id", "event_type", "description", "category", "direction", "amount", "currency", "event_date", "settlement_date", "status", "linked_event_id", "flexibility", "minimum_allowed_amount"),
    "request_payment_options": ("payment_option_id", "request_id", "payment_method", "payment_amount", "number_of_payments", "first_payment_date", "payment_frequency_days", "financing_fee", "total_payable_amount"),
    "messages": ("message_id", "user_id", "request_id", "related_event_id", "sent_at", "source_type", "message_text"),
    "images": ("image_id", "user_id", "request_id", "related_event_id"),
    "exchange_rates": ("rate_date", "from_currency", "to_currency", "rate"),
}


def read_table(path: Path, columns: tuple[str, ...]) -> tuple[dict[str, str], ...]:
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != columns:
            raise DataError(f"{path.name}: expected exact input columns {columns}")
        result = []
        for number, row in enumerate(reader, 2):
            if None in row or any(value is None for value in row.values()):
                raise DataError(f"{path.name}:{number}: malformed CSV row")
            result.append(row)
        return tuple(result)


def unique(rows: tuple[dict[str, str], ...], key: str) -> dict[str, dict[str, str]]:
    result = {}
    for row in rows:
        value = row[key]
        if not value or value in result:
            raise DataError(f"Missing or duplicate {key}: {value!r}")
        result[value] = row
    return result


def load_requests(path: Path) -> tuple[dict[str, str], ...]:
    rows = read_table(path, REQUEST_COLUMNS)
    unique(rows, "request_id")
    if not rows:
        raise DataError("No input requests")
    return rows


@dataclass(frozen=True)
class RawContext:
    request: dict[str, str]
    profile: dict[str, str]
    events: tuple[dict[str, str], ...]
    options: tuple[dict[str, str], ...]
    messages: tuple[dict[str, str], ...]
    images: tuple[dict[str, str], ...]
    rates: tuple[dict[str, str], ...]


def build_context(dataset: Path, request: dict[str, str]) -> RawContext:
    if set(request) != set(REQUEST_COLUMNS):
        raise DataError("Context accepts input fields only; expected outputs are forbidden")
    tables = {name: read_table(dataset / f"{name}.csv", cols) for name, cols in SCHEMAS.items()}
    profiles = unique(tables["financial_profiles"], "user_id")
    events = unique(tables["financial_events"], "event_id")
    for name, key in (("request_payment_options", "payment_option_id"), ("messages", "message_id"), ("images", "image_id")):
        unique(tables[name], key)
    for event in events.values():
        if event["user_id"] not in profiles:
            raise DataError(f"{event['event_id']}: unknown user")
        linked = event["linked_event_id"]
        if linked and (linked not in events or events[linked]["user_id"] != event["user_id"]):
            raise DataError(f"{event['event_id']}: invalid lifecycle link")
    for name in ("messages", "images"):
        for item in tables[name]:
            target = item["related_event_id"]
            if item["user_id"] not in profiles or (target and (target not in events or events[target]["user_id"] != item["user_id"])):
                raise DataError(f"{name}: invalid user/event reference")
    rate_keys = [(r["rate_date"], r["from_currency"], r["to_currency"]) for r in tables["exchange_rates"]]
    if len(rate_keys) != len(set(rate_keys)):
        raise DataError("Duplicate dated currency pair")
    rid, uid = request["request_id"], request["user_id"]
    if uid not in profiles:
        raise DataError(f"{rid}: unknown user {uid}")
    selected = {}
    for name in ("messages", "images"):
        selected[name] = tuple(r for r in tables[name] if r["user_id"] == uid or r["request_id"] == rid)
        for item in selected[name]:
            if item["user_id"] != uid or item["request_id"] not in ("", rid):
                raise DataError(f"{name}: conflicting request/user reference for {rid}")
            if name == "images":
                image_path = dataset / "media" / "images" / f"{item['image_id']}.png"
                if not image_path.is_file():
                    raise DataError(f"Missing linked image: {image_path}")
    options = tuple(r for r in tables["request_payment_options"] if r["request_id"] == rid)
    if not 2 <= len(options) <= 4:
        raise DataError(f"{rid}: expected two to four payment options")
    return RawContext(dict(request), profiles[uid], tuple(r for r in events.values() if r["user_id"] == uid), options, selected["messages"], selected["images"], tables["exchange_rates"])
