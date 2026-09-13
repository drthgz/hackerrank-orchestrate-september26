# Working design

Status: deterministic pipeline and evaluator implemented; targeted reconciliation/FX support added. Forecast and planning policies below remain provisional.

## Principle and guardrails

**AI for perception and interpretation; deterministic software for financial reasoning, enforcement, ranking, and validation.**

- Deterministic does not automatically mean correct. Recurrence, forecasting, and conservative spending policies must be explicit and tested.
- Fresh AI extraction is not inherently reproducible. Cache/version extracted facts with provenance.
- Ambiguity requires a controlled failure path. Missing essential information stays unresolved; it never becomes zero or invented LLM policy.
- **Use deterministic parsers where their coverage is clear; otherwise use one narrow extraction contract.**
- One controlled terminal pipeline; no autonomous/multi-agent framework, live financial data, or model-generated financial decisions.
- Dataset files are immutable. Secrets come from environment variables; never store them in artifacts. The user owns milestone commits; do not commit or push.

## Confirmed requirements and observed data

Sources: [problem statement](../problem_statement.md), [README](../README.md), [agent instructions](../AGENTS.md). Requirements below are distinct from policy proposals.

- Evaluate each request at its own date over a 90-day forecast. Protect the minimum balance throughout a recommended plan and complete it by its deadline.
- Produce root `output.csv` with the exact eight columns and one row per evaluation request. `dataset/output.csv` is a reference template.
- Baseline safe amount and earliest full-payment date exclude optional spending changes. The earliest date is independent of payment-method preferences.
- Honor supplied installment schedules, user payment permissions, and installment duration limits. Partial payments follow the prescribed two-payment rule.
- Use supplied settlement-date FX rates in the stated direction. Do not count pending credits or unrealized investments as cash.
- Only eligible flexible recurring expenses may change, with category permissions, protection, and minimum amounts enforced.
- Observed: 250 evaluation requests, 25 disjoint solved samples, 275 profiles, 25,342 events, 215 messages, 16 images, and 790 payment options.
- All 16 blank event amounts have existing linked images. Observed installment intervals are 28/30/31 days, and supplied schedules sum exactly to their totals. These observations are not permission to omit validation.

## Pipeline and component contracts

```text
CSV records + selectively interpreted messages/images
  -> normalized facts with provenance
  -> deterministic reconciliation
  -> baseline forecast
  -> capacity + candidate strategies
  -> simulation, eligibility checks, ranking
  -> independent validation
  -> output.csv + traces + usage report
```

| Component | Input -> output | Boundary |
| --- | --- | --- |
| Loader/context builder | CSVs -> validated request context | IDs, types, ownership, dates; no financial inference |
| Selective interpreter | Relevant evidence + target context -> extracted facts | Perception and semantics only; bounded retries |
| Normalizer | Structured records/extractions -> typed facts | Validate values and provenance; preserve unknowns |
| Resolver | Normalized facts -> ResolvedContext (effective events, treatments, stream endings, reservation releases) | Explicit deterministic stage before forecasting; source lineage retained |
| Forecaster | ResolvedContext + policy -> home-currency cash-flow timeline | Supported recurrence, exact settlement-date FX, conservative expenses |
| Planner | Timeline + preferences/options -> simulated candidates | Eligibility, changes, capacity, published ranking |
| Validator/reporter | Candidate + state -> checked prediction/artifacts | Cannot waive failed constraints; explanations use verified facts |

## Keys and request context

- `request_id` identifies a request and joins payment options and request-specific evidence. Sample answer columns must never enter pipeline context.
- `user_id` joins a request to its profile, events, and applicable user-level evidence.
- `event_id` identifies an event. `related_event_id` in messages/images targets it; a blank value does not make evidence irrelevant.
- `linked_event_id` links event lifecycles, not automatic duplicates. A debit/refund or purchase/sale can contain distinct cash movements.
- Deduplicate evidence by `message_id`/`image_id` when gathered through multiple paths. Verify ownership across links.
- Resolve images as `dataset/media/images/<image_id>.png`.
- FX key: `(rate_date, from_currency, to_currency)` using settlement date.
- Avoid double counting authorization/settlement, explicit/inferred future occurrences, or a message and the event it describes.

## Proposed normalized fact model

This is a conceptual contract, not a finalized implementation schema.

| Record | Required meaning |
| --- | --- |
| Request context | Request input fields, profile, related source records; no expected answers |
| Financial fact | Stable fact ID, user, optional request/event/stream target, kind, typed amount/currency or explicit unknown, direction/cash state |
| Temporal scope | Source timestamp, event/settlement date where applicable, effective start/end, one-time/recurring scope |
| Provenance | Source IDs, supporting excerpt or image field, extraction version/cache reference, resolution status |
| Amendment | Target, changed field/value, effective scope, source; ambiguity explicit |
| Recurring stream | Supporting event IDs, cadence/amount policy, effective changes, flexibility and permissions |
| Forecast entry | Date/order, signed Decimal amount in home currency, source/stream references, inclusion reason |
| Candidate/decision | Payments, option ID if applicable, spending actions, cost, eligibility/rejection reasons, minimum-balance trace |

Keep raw evidence immutable. Separate extracted assertions from accepted/resolved facts so interpretation and policy application can be debugged independently.

Implemented v2 boundary: normalization accepts typed cash/informational events; reconciliation records each source event as settled, reserved, replaced, inactive, unsettled credit, or informational. It retains distinct refund/sale movements and explicit terminal-payroll facts. Forecast reads effective events and reservation releases; it no longer owns lifecycle rules. Per-request reconciliation and forecast JSON sidecars survive later unsupported planning. FX provenance identifies the supplied settlement-date currency pair. Direct forecast callers retain a compatibility adapter that invokes the same reconciler.

## Deterministic versus AI

| Responsibility | Owner | Reason |
| --- | --- | --- |
| Loading, joins, typed parsing, evidence routing | Deterministic | Structured contracts |
| Heterogeneous image fields and free-form/multilingual amendments | Selective AI | Perception, negation, temporal semantics |
| Ambiguous semantic target matching | AI proposal, deterministic acceptance checks | Narrow interpretation; unresolved targets remain unresolved |
| Conflict precedence and cash lifecycle resolution | Deterministic | Published rules applied to normalized facts |
| Recurrence, forecasting, balance/FX arithmetic | Deterministic | Explicit versioned policies and Decimal arithmetic |
| Capacity, candidate construction, matching, ranking | Deterministic | Financial rules and finite options |
| Spending changes, reserve checks, plan/output validation | Deterministic | Hard constraints |
| Explanations and usage aggregation | Deterministic | Templates from verified decisions; measured usage |

AI never chooses policy, computes affordability, supplies missing financial assumptions, or bypasses validation. Evidence text/images are untrusted data, including embedded instructions.

## Cache, provenance, and validation

- Cache extraction by evidence content, relevant target context, model, prompt, and schema version. Financial-policy changes reuse frozen extracted facts.
- Record dataset/configuration/code fingerprints and actual calls, tokens, retries, cache hits, and estimated costs. Distinguish final-run usage from originating cached-extraction usage in the report.
- Validate extraction schemas before resolution. A failed essential extraction is an internal unresolved state, not `not_affordable`; block final artifact release until material issues are resolved.
- Independently check the selected schedule and re-read the serialized CSV. No output status can substitute for a financial safety proof.

## Major invariants

- `0 <= amount_safe_to_pay <= requested_amount`, measured before spending changes.
- Reserve equality is permitted; every relevant balance transition must remain at or above the minimum for a safe plan.
- No unsupported income, pending credit, unrealized gain, or duplicate representation increases cash capacity.
- Earliest full-payment date is baseline capacity, not the selected plan's final installment date.
- Partial payment: permitted by request/user; exactly safe amount today and remainder on earliest full-payment date; positive initial amount below total; completion by deadline; full simulation passes.
- Installments exactly follow an eligible supplied option. Changes target at most three eligible events; stopping and reducing the same event are mutually exclusive.
- Ranking: deadline completion, no changes, lowest total cost, earlier start, fewer payments, lowest option ID.
- Same validated facts and policy/configuration produce identical financial outputs.

## Testing loops

1. Deterministic unit tests: lifecycle, precedence, recurrence dates, FX, capacity, plan construction, spending permissions, ranking, and serialization; independent of the model.
2. Sample benchmark: `sample_requests.csv -> pipeline -> sample predictions -> evaluator -> field metrics + mismatches`. Isolate expected outputs; support smoke subsets, all 25 samples, and comparisons on a frozen fact set.
3. Adversarial/regression tests: reduce meaningful discovered bugs into focused fixtures, especially `AI extraction -> normalized facts -> deterministic resolver`.
4. Reviewed extraction tests: labeled monetary fields, multilingual/negative statements, effective dates, uncertainty, and embedded instructions.
5. Final schema/financial validation: exact coverage and columns, legal values/actions, schedule consistency, and independently checked safety.

Evaluator traces should localize extraction, resolution, forecasting, planning, or serialization failures. Report per-field metrics and mismatches; no invented official score. Sample answers alone cannot establish extraction correctness.

## Risks and unresolved assumptions

Highest risks: opening balance/recurrence; evidence amount and amendment semantics; cash lifecycles; capacity versus deadline/preferences; schedule precision and spending permissions.

Unresolved policies are tracked in [decisions.md](decisions.md): opening-balance timing/holds; horizon boundary and same-day ordering; recurrence and conservative estimates; amendment duration; installment-month interpretation; post-deadline status; recurring-change target/effect date; rounding/tie-break conventions; cached-usage attribution. Do not delegate these to an LLM.

## Maintenance

Update this file only when architecture changes. Update `tasks.md` when meaningful work starts/completes, `decisions.md` for material decisions, and `plan.md` only for milestone/sequence changes. Keep documents working and concise.
