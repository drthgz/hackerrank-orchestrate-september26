"""Extraction contracts, cache behavior, provenance, and deterministic flow."""

import json
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))

from buy_or_wait.domain import UnsupportedCase
from buy_or_wait.extraction import ExtractionConfig, extract
from buy_or_wait.forecast import build_forecast
from buy_or_wait.loading import RawContext
from buy_or_wait.normalize import normalize


def raw_context(*, messages=(), images=(), amount="", salary_history=False):
    request = dict(request_id="r", user_id="u", request_date="2026-04-03",
                   request_type="purchase", requested_amount="10",
                   desired_completion_date="2026-05-01", allows_partial_payment="false",
                   request_text="Can I buy this?")
    profile = dict(user_id="u", home_currency="EUR", current_available_balance="1000",
                   minimum_balance_to_keep="100", financial_priorities="savings",
                   expense_categories_to_protect="rent",
                   expense_categories_user_is_willing_to_reduce="",
                   expense_categories_user_is_willing_to_stop="",
                   payment_methods_user_will_consider="full_payment", max_installment_months="")
    events = [dict(event_id="target", user_id="u", event_type="expense",
                   description="Linked bill", category="utilities", direction="debit",
                   amount=amount, currency="EUR", event_date="2026-04-02",
                   settlement_date="2026-04-05", status="scheduled", linked_event_id="",
                   flexibility="fixed", minimum_allowed_amount="")]
    if salary_history:
        events = [dict(event_id=f"salary-{month}", user_id="u", event_type="income",
                       description="Employer payroll", category="salary", direction="credit",
                       amount="50", currency="EUR", event_date=f"2026-0{month}-06",
                       settlement_date=f"2026-0{month}-06", status="settled",
                       linked_event_id="", flexibility="fixed", minimum_allowed_amount="")
                  for month in (1, 2, 3)]
    option = dict(payment_option_id="full", request_id="r", payment_method="full_payment",
                  payment_amount="10", number_of_payments="1", first_payment_date="2026-04-03",
                  payment_frequency_days="", financing_fee="0", total_payable_amount="10")
    return RawContext(request, profile, tuple(events), (option,), tuple(messages), tuple(images), ())


def fact(kind="event_amount", value="704.05", target="target", **changes):
    item = {"fact_type": kind, "value": value, "currency": "EUR",
            "effective_date": None, "scope": "event", "target_event_id": target,
            "related_event_ids": [], "category": None, "direction": None,
            "confidence": "high", "evidence": "Amount due 704.05"}
    item.update(changes)
    return item


def response(*facts, input_tokens=100, output_tokens=20):
    return {"output": [{"content": [{"type": "output_text",
                                      "text": json.dumps({"facts": list(facts)})}]}],
            "usage": {"input_tokens": input_tokens, "output_tokens": output_tokens}}


class ExtractionTest(unittest.TestCase):
    def message(self, text, identifier="m"):
        return dict(message_id=identifier, user_id="u", request_id="r", related_event_id="",
                    sent_at="2026-04-01T00:00:00Z", source_type="bank", message_text=text)

    def image(self, identifier="i"):
        return dict(image_id=identifier, user_id="u", request_id="r", related_event_id="target")

    def dataset(self, temporary, identifier="i"):
        root = Path(temporary)
        path = root / "media" / "images"
        path.mkdir(parents=True, exist_ok=True)
        (path / f"{identifier}.png").write_bytes(b"fake-png-content")
        return root

    def test_deterministic_no_cash_message(self):
        message = self.message("The refund has not reached your account yet.")
        result = extract(raw_context(messages=(message,)), Path("unused"),
                         ExtractionConfig(mode="deterministic-only"))
        self.assertEqual(result.context.extracted_facts[0]["fact_type"], "no_material_change")
        self.assertEqual(result.usage, ())

    def test_deterministic_salary_termination_and_percentage_contracts(self):
        cases = [
            ("Your temporary monthly pay is EUR 1037.52. It continues for the next payroll.",
             "stream_amount", "1037.52"),
            ("The current seasonal contract has ended. No off-season income or renewal has been confirmed.",
             "stream_termination", None),
            ("The renewed lease increases monthly rent by 12%. The new amount is used next month.",
             "stream_percent_change", "12"),
        ]
        for text, kind, value in cases:
            with self.subTest(kind=kind):
                result = extract(raw_context(messages=(self.message(text),)), Path("unused"),
                                 ExtractionConfig(mode="deterministic-only"))
                self.assertEqual(result.context.extracted_facts[0]["fact_type"], kind)
                self.assertEqual(result.context.extracted_facts[0]["value"], value)

    def test_explicit_internal_transfer_neutralizes_unique_pair(self):
        left = dict(raw_context().events[0], event_id="left", amount="25", direction="debit")
        right = dict(raw_context().events[0], event_id="right", amount="25", direction="credit")
        message = self.message("The matching debit and credit came from a transfer between your two accounts.")
        raw = replace(raw_context(messages=(message,)), events=(left, right))
        result = extract(raw, Path("unused"), ExtractionConfig(mode="deterministic-only"))
        self.assertEqual(result.context.extracted_facts[0]["fact_type"], "cash_neutral")
        self.assertEqual({event["status"] for event in result.context.events}, {"cancelled"})

    def test_model_fact_normalizes_with_provenance_and_image_amount_flows(self):
        with tempfile.TemporaryDirectory() as temporary:
            dataset = self.dataset(temporary)
            result = extract(raw_context(images=(self.image(),)), dataset,
                             ExtractionConfig(mode="live", cache_dir=dataset / "cache",
                                              caller=lambda payload: response(fact())))
            normalized = normalize(result.context)
            self.assertEqual(str(normalized.events[0].amount), "704.05")
            self.assertEqual(normalized.extracted_facts[0].source.source_id, "i")
            self.assertEqual(normalized.extracted_facts[0].prompt_version, "evidence-facts-v4")
            self.assertTrue(any(entry.entry_id == "target" for entry in build_forecast(normalized).entries))

    def test_image_contract_selects_grounded_balance_due(self):
        with tempfile.TemporaryDirectory() as temporary:
            dataset = self.dataset(temporary)
            total = fact(value="200000", evidence="Total amount 200000")
            due = fact(value="100000", evidence="Balance due 100000")
            result = extract(raw_context(images=(self.image(),)), dataset,
                             ExtractionConfig(mode="live", cache_dir=dataset / "cache",
                                              caller=lambda payload: response(total, due)))
            self.assertEqual(result.context.events[0]["amount"], "100000")

    def test_malformed_low_confidence_and_missing_fact_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            dataset = self.dataset(temporary)
            for output in (response(), response(fact(confidence="low")),
                           response(fact(kind="unresolved", value=None))):
                with self.subTest(output=output), self.assertRaises(UnsupportedCase):
                    extract(raw_context(images=(self.image(),)), dataset,
                            ExtractionConfig(mode="live", cache_dir=dataset / "cache2",
                                             caller=lambda payload, output=output: output))

    def test_failed_extraction_still_reports_measured_usage(self):
        with tempfile.TemporaryDirectory() as temporary:
            dataset = self.dataset(temporary)
            usage = []
            with self.assertRaises(UnsupportedCase):
                extract(raw_context(images=(self.image(),)), dataset,
                        ExtractionConfig(mode="live", cache_dir=dataset / "cache",
                                         caller=lambda payload: response(fact(confidence="low"))),
                        usage)
            self.assertEqual(len(usage), 1)
            self.assertEqual(usage[0].model_calls, 1)

    def test_conflicting_facts_fail(self):
        with tempfile.TemporaryDirectory() as temporary:
            dataset = Path(temporary)
            message = self.message("The bill amount is 10, corrected amount is 11.")
            message["related_event_id"] = "target"
            with self.assertRaisesRegex(UnsupportedCase, "Conflicting"):
                extract(raw_context(messages=(message,)), dataset,
                        ExtractionConfig(mode="live", cache_dir=dataset / "cache",
                                         caller=lambda payload: response(fact(value="10"), fact(value="11"))))

    def test_cache_hit_miss_and_cached_zero_calls(self):
        with tempfile.TemporaryDirectory() as temporary:
            dataset = self.dataset(temporary)
            cache = dataset / "cache"
            calls = []
            config = ExtractionConfig(mode="live", cache_dir=cache,
                                      caller=lambda payload: calls.append(payload) or response(fact()))
            first = extract(raw_context(images=(self.image(),)), dataset, config)
            second = extract(raw_context(images=(self.image(),)), dataset,
                             replace(config, mode="cached", caller=lambda payload: self.fail("called")))
            self.assertEqual(len(calls), 1)
            self.assertEqual(first.usage[0].cache_misses, 1)
            self.assertEqual(second.usage[0].model_calls, 0)
            self.assertEqual(second.usage[0].cache_hits, 1)
            with self.assertRaisesRegex(UnsupportedCase, "cache miss"):
                extract(raw_context(images=(self.image("other"),)), self.dataset(temporary, "other"),
                        replace(config, mode="cached"))

    def test_cache_version_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as temporary:
            dataset = self.dataset(temporary)
            cache = dataset / "cache"
            result = extract(raw_context(images=(self.image(),)), dataset,
                             ExtractionConfig(mode="live", cache_dir=cache,
                                              caller=lambda payload: response(fact())))
            path = cache / f"{result.cache_keys[0]}.json"
            value = json.loads(path.read_text())
            value["schema_version"] = "old"
            path.write_text(json.dumps(value))
            with self.assertRaisesRegex(UnsupportedCase, "version mismatch"):
                extract(raw_context(images=(self.image(),)), dataset,
                        ExtractionConfig(mode="cached", cache_dir=cache))

    def test_stream_amendment_modifies_only_target_category(self):
        message = self.message("Salary changes to EUR 100 from 2026-04-06")
        amendment = fact("stream_amount", "100", target=None, currency="EUR",
                         effective_date="2026-04-06", scope="ongoing",
                         category="salary", direction="credit", evidence="Salary changes to EUR 100")
        result = extract(raw_context(messages=(message,), salary_history=True), Path("unused"),
                         ExtractionConfig(mode="live", cache_dir=Path(tempfile.mkdtemp()),
                                          caller=lambda payload: response(amendment)))
        forecast = build_forecast(normalize(result.context))
        salary_entries = [entry for entry in forecast.entries if entry.amount > 0]
        self.assertTrue(salary_entries)
        self.assertTrue(all(entry.amount == 100 for entry in salary_entries))
        self.assertTrue(all("m" in entry.source_ids for entry in salary_entries))

    def test_deterministic_only_preserves_missing_amount(self):
        with tempfile.TemporaryDirectory() as temporary:
            dataset = self.dataset(temporary)
            raw = raw_context(images=(self.image(),))
            with self.assertRaisesRegex(UnsupportedCase, "needs model"):
                extract(raw, dataset, ExtractionConfig(mode="deterministic-only"))
            self.assertEqual(raw.events[0]["amount"], "")


if __name__ == "__main__":
    unittest.main()
