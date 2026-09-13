# Documentation Review 04: Targeted Deterministic Correctness Phase

**Repository:** HackerRank Orchestrate - Buy or Wait?  
**Review date:** 2026-09-13  
**Scope:** Targeted deterministic reconciliation, terminal-income handling,
non-cash normalization, FX conversion, tests, and the final v2 sample run.
This review is advisory; no code or existing documentation was changed.

## 1. Executive assessment

This phase was completed responsibly. The team corrected the known
`request_05` false-positive mechanism, resolved both normalization failures,
added explicit reconciliation/provenance behavior, introduced narrow terminal
payroll handling, and added exact settlement-date FX conversion. The reported
65-test suite passes, and the final v2 run has zero failed requests.

The most important success is safety behavior: `request_05` is now withheld
because the engine cannot justify a safe plan, rather than emitting an
overconfident affordability recommendation. The phase also avoided the common
failure mode of tuning expense estimates to force a sample label.

However, the final sample run processes only **1/25** requests. The apparent
structured accuracy of **1/1 among processed requests** is therefore not
evidence of broad financial correctness. The phase improved correctness and
reconciliation foundations, but it did not materially increase challenge
coverage. The next phase should focus on general planning and supported
recurrence/evidence policies, not further narrow safety patches.

**Current maturity:** strong deterministic safety/reconciliation increment;
still far from a submission-ready full-dataset decision engine.

## 2. Validation and evidence reviewed

### Tests

- Reported result: **65 tests passed**, including 19 new regressions.
- The new coverage addresses terminal payroll, valid non-cash events,
  lifecycle reconciliation, reservation release, and FX conversion.
- Existing evaluator and vertical-slice tests remain part of the suite.

### Final v2 run

Artifact: `artifacts/evaluation/deterministic-core-v2-final/`

| Measure | Result |
|---|---:|
| Selected solved samples | 25 |
| Processed | 1 |
| Unsupported | 24 |
| Failed | 0 |
| Fully matching structured rows | 1 |
| Comparable financial mismatches | 0 |
| Missing prediction fields | 144 |
| Explanation exact matches | 0 |
| Model calls/tokens/cost | 0/0/0 |

The final policy is versioned as `deterministic-core-v2`, with dataset and source
fingerprints recorded in metadata. The run correctly preserves missing
predictions as missing rather than fabricating financial outputs.

## 3. What was completed well

### 3.1 The false-positive was corrected at the cause

The prior trace identified invented post-terminal salary credits as the cause
of `request_05`'s unsafe affordability output. The new narrow parser treats the
exact terminal-payroll marker as stream-ending evidence and does not loosen
expense thresholds merely to match the sample's expected amount.

This is a strong engineering decision: it addresses unsupported future income
rather than fitting the result to a request-specific label.

### 3.2 Non-cash events are now represented safely

The prior `direction=non_cash` normalization failures are resolved. Unrealized
investment valuations can be represented without being treated as cash
available for spending. This is directly aligned with the challenge contract.

### 3.3 Lifecycle semantics moved to an explicit reconciliation stage

The new reconciliation boundary preserves raw events, effective movements,
lineage, stream endings, and reservation-release behavior. It avoids treating
every `linked_event_id` as an instruction to delete the earlier record. That is
safer than opportunistic deduplication in the forecast layer.

### 3.4 FX conversion is implemented in the correct direction and time basis

Exact Decimal conversion at settlement dates, including inferred future
occurrences, matches the documented challenge rule. The phase correctly avoids
latest-rate reuse, reversed rates, interpolation, or invented future rates.

### 3.5 Fail-closed behavior is preserved

`request_05` now ends at the planning boundary with an explicit unsupported
diagnostic because later/partial/installment planning is not implemented. That
is preferable to emitting an unsafe recommendation and is consistent with the
repository's unresolved-evidence policy.

## 4. Findings

### F-01 — Critical: coverage regressed from 2/25 to 1/25

The final v2 run processes one sample, compared with two in baseline-v1. This
is not necessarily a regression in correctness—the unsafe `request_05` output
was correctly withheld—but it means the new core has not yet expanded usable
decision coverage.

**Recommendation:** Track coverage as a first-class phase exit metric. Do not
describe the v2 result as improved benchmark accuracy without stating that
coverage decreased and that the only processed row is `request_09`.

### F-02 — High: “zero comparable mismatches” is conditional on one prediction

The final run reports zero comparable financial mismatches because the only
processed request matches. The other 24 requests have no prediction, producing
144 missing financial fields.

**Recommendation:** Make the headline metric:

```text
end-to-end structured accuracy: 1/25 = 4%
coverage: 1/25 = 4%
conditional accuracy: 1/1 = 100%
```

Keep “zero comparable mismatches” as a secondary diagnostic, never as the
primary correctness claim.

### F-03 — High: planning is now the immediate blocker

`request_05` is correctly withheld because immediate full payment is unsafe,
but the planner still lacks later, partial-payment, installment, spending-change,
and general safe-capacity strategies. This is now a known capability gap rather
than a hidden false-positive.

**Impact:** A safe refusal at planning is not yet a valid final challenge output.
The final system must eventually produce a recommendation for every resolvable
request and independently validate it.

**Recommendation:** Implement candidate planning in this order:

1. baseline safe amount and earliest safe full-payment date;
2. wait/later;
3. exact supplied installment options;
4. prescribed partial payment;
5. eligible flexible spending changes and re-simulation;
6. published ranking and final status/method consistency.

### F-04 — High: recurrence policy remains too narrow and can suppress valid cases

The final results still show recurrence rejection for request_01 due to variable
grocery amounts. The current policy intentionally rejects this uncertainty,
which is safe, but it prevents conservative treatment of variable essential
spending required by the challenge.

**Recommendation:** Define a general evidence-based recurring-stream policy:
identity, cadence tolerance, variable-expense estimator, month-end behavior,
terminal/amendment scope, and explicit-occurrence deduplication. Compare
candidate policies on frozen facts and adversarial fixtures. Do not replace
uncertainty with zero or an optimistic average.

### F-05 — High: household income and multiple-source identity remain unresolved

The phase deliberately defers request_13's multiple household income streams
and disappearing second stream. Category-level stream identity remains
provisional.

**Recommendation:** Model stream identity using source/user/event provenance and
effective periods rather than only `(event_type, category, direction)`. Require
evidence for continuation or termination of each source. Add fixtures for
multiple employers, changing salary, overlapping streams, and one-time credits.

### F-06 — Medium: FX support is only partially validated at end to end

The phase adds exact FX conversion and clears the direct FX blocker for
request_25, but request_25 remains unsupported because transport cadence is not
implemented. Therefore the run demonstrates FX support at focused scope, not a
completed mixed-currency decision path.

**Recommendation:** Retain focused FX tests and add an end-to-end case where a
converted movement affects capacity and plan safety. Record the rate key and
converted amount in the balance trace.

### F-07 — Medium: reconciliation semantics need broader lifecycle coverage

The accepted reconciliation policy is substantially stronger, but the final
challenge still contains refunds, failed retries, investments, authorization/
settlement pairs, pending reservations, and potentially duplicate debits.

**Recommendation:** Add a lifecycle coverage matrix with each source status/link
pattern, expected effective cash movement, reservation treatment, and release
date. Require every supported row to retain lineage and every unsupported
relationship to produce a stable blocker code.

### F-08 — Medium: final output validation remains ahead of planner capability

The current validator can structurally validate the one processed full-payment
row, but the challenge-specific checks for installments, partial payment,
spending changes, and full balance safety remain unexercised in this phase.

**Recommendation:** Add contract tests before implementing each planner strategy,
then independently validate serialized output against the resolved context. A
strategy should not be considered complete until its positive and negative
fixtures pass after CSV round-trip.

### F-09 — Low: diagnostics should distinguish intentional withholding from failure

The final output uses `unsupported` at the planning stage for request_05. That
is correct for development, but the diagnostic should eventually carry a stable
reason such as `NO_IMPLEMENTED_SAFE_STRATEGY` or `INSUFFICIENT_FORECAST_SUPPORT`,
separate from implementation exceptions and malformed input.

**Recommendation:** Add blocker codes and severity to evaluator artifacts while
retaining human-readable diagnostics.

## 5. Phase verdict

| Dimension | Verdict |
|---|---|
| Safety improvement | **Strong** — unsafe request_05 recommendation withheld. |
| Root-cause analysis | **Strong** — terminal income identified and addressed without label fitting. |
| Data modeling | **Improved** — non-cash and lifecycle boundaries are clearer. |
| FX correctness | **Improved** — exact settlement-date conversion added. |
| Test discipline | **Strong** — 65 tests and focused regressions reported. |
| Sample coverage | **Insufficient** — 1/25 processed. |
| Final challenge readiness | **Not ready** — planning, evidence, and full output coverage remain. |

## 6. Prioritized next steps

### P0 — build general deterministic planning

- Implement safe-capacity search and earliest full-payment date.
- Implement wait/later and exact installment candidate simulation.
- Implement partial-payment semantics exactly as specified.
- Add context-aware plan validation after serialization.
- Preserve the request_05 terminal-income regression permanently.

### P1 — broaden financial-state reconstruction

- Define variable essential-spending policy.
- Resolve multi-source income identity and continuation.
- Complete lifecycle matrix and stable blocker taxonomy.
- Add end-to-end mixed-currency capacity tests.
- Add eligible spending-change generation and ranking.

### P2 — prepare evidence and release

- Add reviewed message/image extraction with provenance and cache versioning.
- Add a 250-request release runner independent of sample answers.
- Generate the required nonempty final usage report from the authoritative run.
- Retain full traces, manifests, output validation, and package inspection.

## 7. Recommended next-milestone acceptance criteria

- [ ] All 65 tests remain green.
- [ ] `request_05` remains withheld without a request-ID-specific rule.
- [ ] At least one new strategy beyond immediate full payment is exercised
  end-to-end and independently safety-validated.
- [ ] Coverage increases from 1/25 with no unsafe recommendation regressions.
- [ ] Request_01's variable-essential-spending behavior is defined by policy and
  tested, not silently averaged.
- [ ] Request_13's multiple-income behavior is explicitly resolved or classified
  with a stable blocker.
- [ ] Request_25 has a mixed-currency end-to-end regression once cadence/planning
  support exists.
- [ ] Final metrics separate coverage, end-to-end accuracy, conditional accuracy,
  missing fields, and comparable mismatches.
