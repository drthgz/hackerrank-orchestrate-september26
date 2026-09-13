"""Selective evidence-to-fact extraction. No financial decisions or forecasting."""

import base64
import hashlib
import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Callable

from .domain import DataError, UnsupportedCase
from .loading import RawContext

PROMPT_VERSION = "evidence-facts-v4"
SCHEMA_VERSION = "evidence-fact-schema-v2"
DEFAULT_MODEL = "gpt-5-mini"

FACT_TYPES = (
    "event_amount", "event_settlement_date", "event_amount_date", "cash_state",
    "stream_amount", "stream_percent_change", "stream_termination", "cash_neutral", "one_time",
    "no_material_change", "unresolved",
)

FACT_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {"facts": {"type": "array", "items": {
        "type": "object", "additionalProperties": False,
        "properties": {
            "fact_type": {"type": "string", "enum": list(FACT_TYPES)},
            "value": {"type": ["string", "null"]},
            "currency": {"type": ["string", "null"]},
            "effective_date": {"type": ["string", "null"]},
            "scope": {"type": "string", "enum": ["event", "one_occurrence", "ongoing", "informational"]},
            "target_event_id": {"type": ["string", "null"]},
            "related_event_ids": {"type": "array", "items": {"type": "string"}},
            "category": {"type": ["string", "null"]},
            "direction": {"type": ["string", "null"], "enum": ["debit", "credit", "non_cash", None]},
            "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
            "evidence": {"type": "string"},
        },
        "required": ["fact_type", "value", "currency", "effective_date", "scope",
                     "target_event_id", "related_event_ids", "category", "direction",
                     "confidence", "evidence"],
    }}}, "required": ["facts"],
}

INSTRUCTIONS = """Extract financial facts only from the supplied evidence.
Do not decide affordability, forecast balances, recommend payment methods, rank plans,
or invent financial policy. Do not infer unsupported values. Return only the defined
schema. Use unresolved when a material value, target, date, currency, or scope is not
supported. Quote a short supporting fragment in evidence. Use event_amount only for
the amount represented by the target event (for a payslip use net pay; for a receipt,
bill, or outstanding balance use the amount actually due for that event). Stream facts
must identify category, direction, effective date, and one_occurrence or ongoing scope.
Candidate events are identifiers and targeting context only. Their fields are not evidence.
Never emit a fact whose value comes only from candidate-event context. Do not emit facts
about unrelated candidate events. For a message that confirms existing treatment without
supplying a new amount/date/state, emit one no_material_change fact.
Only evidence_text or pixels in the input image are evidence. Request fields are context,
not evidence. For an image with a target_event_id, return exactly one event_amount fact
for that target; do not return line items, subtotals, deductions, alternative totals,
or printed dates.
Use stream_percent_change for an explicit percentage change to a recurring stream; put
the unsigned percentage in value and let the supporting evidence state increase/decrease.
"""


@dataclass(frozen=True)
class ExtractionUsage:
    provider: str
    model: str
    model_calls: int
    input_tokens: int
    output_tokens: int
    retries: int
    cache_hits: int
    cache_misses: int
    estimated_cost: Decimal | None


@dataclass(frozen=True)
class ExtractionConfig:
    mode: str = "disabled"
    cache_dir: Path = Path("artifacts/extraction-cache")
    model: str = DEFAULT_MODEL
    provider: str = "openai"
    caller: Callable[[dict], dict] | None = None


@dataclass(frozen=True)
class ExtractionResult:
    context: RawContext
    usage: tuple[ExtractionUsage, ...]
    cache_keys: tuple[str, ...]


def _load_api_key() -> str:
    key = os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI_KEY")
    if key:
        return key
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            name, separator, value = line.partition("=")
            if separator and name.strip() in {"OPENAI_API_KEY", "OPENAI_KEY"}:
                key = value.strip().strip("'\"")
                if key:
                    return key
    raise UnsupportedCase("Live extraction requires OPENAI_API_KEY or OPENAI_KEY")


def _openai_call(payload: dict) -> dict:
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {_load_api_key()}", "Content-Type": "application/json"},
        method="POST")
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise UnsupportedCase(f"OpenAI extraction request failed ({exc.code}): {detail}") from exc
    except urllib.error.URLError as exc:
        raise UnsupportedCase(f"OpenAI extraction request failed: {exc.reason}") from exc


def _response_text(response: dict) -> str:
    if isinstance(response.get("output_text"), str):
        return response["output_text"]
    texts = [part.get("text") for item in response.get("output", [])
             for part in item.get("content", []) if part.get("type") == "output_text"]
    if len(texts) != 1 or not isinstance(texts[0], str):
        raise UnsupportedCase("Model response has no single structured text output")
    return texts[0]


def _validate_fact(fact: dict, event_ids: set[str]) -> None:
    expected = set(FACT_SCHEMA["properties"]["facts"]["items"]["required"])
    if set(fact) != expected or fact["fact_type"] not in FACT_TYPES:
        raise UnsupportedCase("Malformed extracted fact schema")
    if fact["confidence"] != "high":
        raise UnsupportedCase("Material evidence extraction is not high confidence")
    if fact["fact_type"] == "unresolved":
        raise UnsupportedCase(f"Evidence remains unresolved: {fact['evidence']}")
    targets = ([fact["target_event_id"]] if fact["target_event_id"] else []) + fact["related_event_ids"]
    if any(target not in event_ids for target in targets):
        raise DataError("Extracted fact references an event outside the request user")
    if fact["effective_date"]:
        try:
            parsed = datetime.strptime(fact["effective_date"], "%Y-%m-%d").date()
        except ValueError as exc:
            raise UnsupportedCase("Extracted fact has invalid ISO date") from exc
        if parsed.isoformat() != fact["effective_date"]:
            raise UnsupportedCase("Extracted fact has noncanonical date")
    if fact["fact_type"] in {"event_amount", "event_amount_date", "stream_amount",
                             "stream_percent_change"}:
        if not fact["value"] or not re.fullmatch(r"\d+(?:\.\d+)?", fact["value"]):
            raise UnsupportedCase("Extracted amount is missing or malformed")


def _ground_facts(source_type: str, source: dict, extracted: dict,
                  context: RawContext | None = None) -> dict:
    facts = [fact for fact in extracted.get("facts", []) if fact.get("confidence") == "high"]
    if source_type == "image":
        target = source.get("related_event_id")
        facts = [fact for fact in facts if fact.get("fact_type") == "event_amount"
                 and fact.get("target_event_id") == target]
        if len(facts) > 1:
            preferred = ("net pay", "balance due", "amount due", "net amount", "item bill")
            facts = [fact for fact in facts
                     if any(term in fact.get("evidence", "").casefold() for term in preferred)]
        if len(facts) != 1:
            raise UnsupportedCase("Image did not yield exactly one linked event amount")
        facts[0]["scope"] = "event"
        # The image contract is amount-only. Ignore incidental document dates
        # rather than letting them amend the structured settlement date.
        facts[0]["effective_date"] = None
        facts[0]["related_event_ids"] = []
    else:
        text_digits = re.sub(r"\D", "", source.get("message_text", ""))
        grounded = []
        for fact in facts:
            if (fact.get("fact_type") == "event_settlement_date"
                    and not fact.get("target_event_id") and context is not None):
                scheduled_salary = [event for event in context.events
                                    if event["category"] == "salary"
                                    and event["status"] in {"pending", "scheduled"}]
                if len(scheduled_salary) == 1:
                    fact["target_event_id"] = scheduled_salary[0]["event_id"]
                elif ("confirmed salary is now expected" in source.get("message_text", "").casefold()
                      or "replaces the payroll date" in source.get("message_text", "").casefold()):
                    settled_salary = [event for event in context.events
                                      if event["category"] == "salary" and event["status"] == "settled"]
                    if settled_salary:
                        latest_date = max(event["settlement_date"] for event in settled_salary)
                        latest = [event for event in settled_salary
                                  if event["settlement_date"] == latest_date]
                        if len(latest) == 1:
                            fact["target_event_id"] = latest[0]["event_id"]
            if (fact.get("fact_type") == "event_amount" and not fact.get("target_event_id")
                    and fact.get("category") and fact.get("direction")
                    and fact.get("scope") in {"one_occurrence", "ongoing"}):
                fact["fact_type"] = "stream_amount"
            # Drop internally incomplete assertions before confidence validation.
            # They carry no usable claim and must not make a separate grounded
            # fact unusable (for example, a confirmation plus a speculative date).
            if fact.get("fact_type") in {"event_settlement_date", "event_amount_date"} \
                    and (not fact.get("target_event_id") or not fact.get("effective_date")):
                continue
            if fact.get("fact_type") in {"stream_amount", "stream_percent_change"} \
                    and (not fact.get("value") or not fact.get("category")
                         or not fact.get("direction")):
                continue
            if fact.get("fact_type") == "stream_termination" \
                    and (not fact.get("category") or not fact.get("direction")
                         or not fact.get("effective_date")):
                continue
            if fact.get("fact_type") == "cash_neutral" \
                    and len(fact.get("related_event_ids", [])) != 2:
                continue
            value = fact.get("value")
            if fact.get("fact_type") in {"event_amount", "event_amount_date", "stream_amount",
                                         "stream_percent_change"}:
                value_digits = re.sub(r"\D", "", value or "")
                if value_digits and value_digits not in text_digits:
                    continue
            grounded.append(fact)
        facts = grounded
        if not facts:
            raise UnsupportedCase("Message facts are not grounded in message text")
    for fact in facts:
        if fact.get("fact_type") in {"event_amount", "event_amount_date", "stream_amount",
                                     "stream_percent_change"}:
            fact["value"] = re.sub(r"^(?:[A-Z]{3}|[^\d.-])+", "", fact.get("value") or "")
            fact["value"] = fact["value"].replace(",", "").replace(" ", "").rstrip("%")
    return {"facts": facts}


def _deterministic_message_fact(message: dict, context: RawContext) -> dict | None:
    text = " ".join(message["message_text"].casefold().split())
    if "matching debit and credit" in text and "transfer between your two accounts" in text:
        candidates = [event for event in context.events
                      if event["direction"] in {"debit", "credit"} and event["amount"]]
        pairs = [(left, right) for index, left in enumerate(candidates)
                 for right in candidates[index + 1:]
                 if left["amount"] == right["amount"]
                 and left["direction"] != right["direction"]]
        if len(pairs) == 1:
            return {"fact_type": "cash_neutral", "value": None, "currency": None,
                    "effective_date": None, "scope": "informational",
                    "target_event_id": None,
                    "related_event_ids": [event["event_id"] for event in pairs[0]],
                    "category": "transfer", "direction": None,
                    "confidence": "high", "evidence": message["message_text"][:240]}
        if not pairs:
            return {"fact_type": "no_material_change", "value": None, "currency": None,
                    "effective_date": None, "scope": "informational",
                    "target_event_id": None, "related_event_ids": [],
                    "category": "transfer", "direction": None,
                    "confidence": "high", "evidence": message["message_text"][:240]}
        return None
    if "seasonal contract has ended" in text and "no off-season income or renewal" in text:
        return {"fact_type": "stream_termination", "value": None, "currency": None,
                "effective_date": message["sent_at"][:10], "scope": "ongoing",
                "target_event_id": None, "related_event_ids": [],
                "category": "salary", "direction": "credit", "confidence": "high",
                "evidence": message["message_text"][:240]}
    salary = re.search(r"(?:monthly pay is|next salary is reduced to)\s+([a-z]{3})\s+(\d[\d,]*(?:\.\d+)?)", text)
    if salary and ("next payroll" in text or "next payslip" in text):
        return {"fact_type": "stream_amount", "value": salary.group(2).replace(",", ""),
                "currency": salary.group(1).upper(), "effective_date": None,
                "scope": "one_occurrence", "target_event_id": None,
                "related_event_ids": [], "category": "salary", "direction": "credit",
                "confidence": "high", "evidence": message["message_text"][:240]}
    rent_change = re.search(r"monthly rent by\s+(\d+(?:\.\d+)?)%", text)
    if rent_change and "increase" in text:
        return {"fact_type": "stream_percent_change", "value": rent_change.group(1),
                "currency": None, "effective_date": None, "scope": "ongoing",
                "target_event_id": None, "related_event_ids": [],
                "category": "rent", "direction": "debit", "confidence": "high",
                "evidence": message["message_text"][:240]}
    no_cash_phrases = (
        "has not reached your account yet", "has not been credited", "isn't withdrawable",
        "isn’t withdrawable",
        "no cash proceeds have been generated", "belum disetujui", "masih menunggu",
    )
    if any(phrase in text for phrase in no_cash_phrases):
        return {"fact_type": "no_material_change", "value": None, "currency": None,
                "effective_date": None, "scope": "informational",
                "target_event_id": message["related_event_id"] or None,
                "related_event_ids": [], "category": None, "direction": None,
                "confidence": "high", "evidence": message["message_text"][:240]}
    if "claim is now closed" in text and "no further scheduled payments" in text:
        return {"fact_type": "one_time", "value": None, "currency": None,
                "effective_date": None, "scope": "event",
                "target_event_id": message["related_event_id"] or None,
                "related_event_ids": [], "category": None, "direction": None,
                "confidence": "high", "evidence": message["message_text"][:240]}
    return None


def _candidate_events(context: RawContext, related_event_id: str) -> list[dict]:
    if related_event_id:
        return [event for event in context.events if event["event_id"] == related_event_id]
    dated = sorted(context.events, key=lambda event: (event["settlement_date"], event["event_id"]), reverse=True)
    future = [event for event in dated if event["status"] in {"scheduled", "pending"}]
    salaries = [event for event in dated if event["category"] == "salary"]
    chosen = {event["event_id"]: event for event in future + salaries[:12] + dated[:8]}
    return list(chosen.values())


def _payload(context: RawContext, source_type: str, source: dict, dataset: Path,
             model: str) -> tuple[dict, str]:
    identifier = source[f"{source_type}_id"]
    target = source.get("related_event_id", "")
    candidates = [{key: event[key] for key in ("event_id", "event_type", "description",
                                               "category", "direction", "status")}
                  for event in _candidate_events(context, target)]
    evidence_text = source.get("message_text", "")
    content = [{"type": "input_text", "text": json.dumps({
        "source_type": source_type, "source_id": identifier,
        "request": context.request, "profile_currency": context.profile["home_currency"],
        "target_event_id": target or None, "candidate_events": candidates,
        "evidence_text": evidence_text,
    }, ensure_ascii=False)}]
    content_hash = hashlib.sha256(evidence_text.encode("utf-8")).hexdigest()
    if source_type == "image":
        image_path = dataset / "media" / "images" / f"{identifier}.png"
        data = image_path.read_bytes()
        content_hash = hashlib.sha256(data).hexdigest()
        content.append({"type": "input_image",
                        "image_url": "data:image/png;base64," + base64.b64encode(data).decode("ascii")})
    payload = {"model": model, "instructions": INSTRUCTIONS, "reasoning": {"effort": "minimal"},
               "input": [{"role": "user", "content": content}],
               "text": {"format": {"type": "json_schema", "name": "evidence_facts",
                                    "strict": True, "schema": FACT_SCHEMA}}}
    identity = json.dumps({"content_sha256": content_hash, "source_type": source_type,
                           "source_id": identifier, "target": target, "candidates": candidates,
                           "model": model, "prompt": PROMPT_VERSION, "schema": SCHEMA_VERSION},
                          sort_keys=True, separators=(",", ":"))
    return payload, hashlib.sha256(identity.encode("utf-8")).hexdigest()


def _cost(model: str, input_tokens: int, output_tokens: int) -> Decimal | None:
    if model != "gpt-5-mini":
        return None
    return (Decimal(input_tokens) * Decimal("0.25")
            + Decimal(output_tokens) * Decimal("2.00")) / Decimal("1000000")


def extract(context: RawContext, dataset: Path,
            config: ExtractionConfig = ExtractionConfig(),
            usage_sink: list[ExtractionUsage] | None = None) -> ExtractionResult:
    if config.mode not in {"disabled", "deterministic-only", "cached", "live"}:
        raise ValueError("Unknown extraction mode")
    sources = [("message", item) for item in context.messages] + [("image", item) for item in context.images]
    if not sources:
        return ExtractionResult(context, (), ())
    if config.mode == "disabled":
        return ExtractionResult(context, (), ())
    event_ids = {event["event_id"] for event in context.events}
    facts, usage, cache_keys = [], [], []
    caller = config.caller or _openai_call
    for source_type, source in sources:
        deterministic = _deterministic_message_fact(source, context) if source_type == "message" else None
        if deterministic:
            extracted = {"facts": [deterministic]}
            provider, model = "deterministic", "explicit-patterns-v1"
        else:
            if config.mode == "deterministic-only":
                raise UnsupportedCase(f"Evidence {source[source_type + '_id']} needs model extraction")
            payload, cache_key = _payload(context, source_type, source, dataset, config.model)
            cache_keys.append(cache_key)
            cache_path = config.cache_dir / f"{cache_key}.json"
            if cache_path.is_file():
                cached = json.loads(cache_path.read_text(encoding="utf-8"))
                if cached.get("prompt_version") != PROMPT_VERSION or cached.get("schema_version") != SCHEMA_VERSION:
                    raise UnsupportedCase("Extraction cache version mismatch")
                extracted = cached["result"]
                usage.append(ExtractionUsage(config.provider, config.model, 0, 0, 0, 0, 1, 0, Decimal("0")))
                if usage_sink is not None:
                    usage_sink.append(usage[-1])
            elif config.mode == "cached":
                raise UnsupportedCase(f"Extraction cache miss for {source[source_type + '_id']}")
            else:
                response = caller(payload)
                try:
                    extracted = json.loads(_response_text(response))
                except (json.JSONDecodeError, TypeError) as exc:
                    raise UnsupportedCase("Malformed model JSON output") from exc
                measured = response.get("usage", {})
                input_tokens = measured.get("input_tokens")
                output_tokens = measured.get("output_tokens")
                if not isinstance(input_tokens, int) or not isinstance(output_tokens, int):
                    input_tokens = output_tokens = 0
                    estimated = None
                else:
                    estimated = _cost(config.model, input_tokens, output_tokens)
                usage.append(ExtractionUsage(config.provider, config.model, 1, input_tokens,
                                             output_tokens, 0, 0, 1, estimated))
                if usage_sink is not None:
                    usage_sink.append(usage[-1])
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                cache_path.write_text(json.dumps({
                    "prompt_version": PROMPT_VERSION, "schema_version": SCHEMA_VERSION,
                    "provider": config.provider, "model": config.model,
                    "created_at": datetime.now(timezone.utc).isoformat(), "result": extracted,
                }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            provider, model = config.provider, config.model
        if set(extracted) != {"facts"} or not isinstance(extracted["facts"], list) or not extracted["facts"]:
            raise UnsupportedCase("Evidence extraction returned no facts")
        extracted = _ground_facts(source_type, source, extracted, context)
        for fact in extracted["facts"]:
            _validate_fact(fact, event_ids)
            facts.append({**fact, "source_type": source_type,
                          "source_id": source[source_type + "_id"], "provider": provider,
                          "model": model, "prompt_version": PROMPT_VERSION,
                          "schema_version": SCHEMA_VERSION})

    # Exact event patches are applied before typed normalization. Stream facts
    # remain assertions for the downstream stream/forecast boundary.
    events = [dict(event) for event in context.events]
    by_id = {event["event_id"]: event for event in events}
    assignments = {}
    for fact in facts:
        target = fact["target_event_id"]
        if fact["fact_type"] in {"event_amount", "event_amount_date"}:
            if not target:
                raise UnsupportedCase("Event amount fact has no target")
            if fact["currency"] and fact["currency"] != by_id[target]["currency"]:
                raise UnsupportedCase("Extracted event currency conflicts with structured currency")
            key = (target, "amount")
            if key in assignments and assignments[key] != fact["value"]:
                raise UnsupportedCase("Conflicting extracted amounts for one event")
            assignments[key] = fact["value"]
            by_id[target]["amount"] = fact["value"]
        if fact["fact_type"] in {"event_settlement_date", "event_amount_date"}:
            if not target or not fact["effective_date"]:
                raise UnsupportedCase("Event date fact has no target/date")
            by_id[target]["settlement_date"] = fact["effective_date"]
        if fact["fact_type"] == "cash_state":
            if not target or fact["value"] not in {"settled", "pending", "scheduled", "cancelled"}:
                raise UnsupportedCase("Invalid extracted cash state")
            by_id[target]["status"] = fact["value"]
        if fact["fact_type"] == "cash_neutral":
            if len(fact["related_event_ids"]) != 2:
                raise UnsupportedCase("Cash-neutral fact requires exactly two events")
            for event_id in fact["related_event_ids"]:
                by_id[event_id]["status"] = "cancelled"
    return ExtractionResult(replace(context, events=tuple(events), extracted_facts=tuple(facts)),
                            tuple(usage), tuple(cache_keys))
