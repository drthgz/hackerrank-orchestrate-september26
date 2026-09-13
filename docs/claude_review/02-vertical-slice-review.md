# Documentation Review 02: Simplest Pipeline Vertical Slice

**Repository:** HackerRank Orchestrate - Buy or Wait?  
**Review date:** 2026-09-13  
**Scope:** Review of the implemented vertical slice, its documentation, tests,
and evaluation scaffolding. This review is advisory; no code or existing
documentation was changed.

## 1. Executive assessment

The simplest pipeline is a credible and well-bounded vertical slice, not a
submission-capable solution yet. Its strongest decisions are explicit refusal
of unsupported cases, input-only application boundaries, Decimal/date
normalization, staged atomic output writing, and independent structural
validation. The focused suite passes **29 tests**, and the documented
`request_09` smoke run completes successfully.

The implementation is honest about its limits, which is important for a
financial task. However, the current implementation intentionally supports only
one narrow case: a safe, eligible, fee-free, immediate full payment with no
evidence, FX, complex lifecycle, partial-payment, installment, wait, or
spending-change processing. It therefore cannot yet process the evaluation set
or satisfy the core decision coverage required by the hackathon.

**Current maturity:** sound vertical-slice foundation; not yet a benchmarkable
financial decision engine or release candidate.

## 2. Validation performed

Observed during this review:

- `python3 -B -m unittest discover -s tests -v`: **29 tests passed**.
- `python3 -B scripts/run_vertical_slice.py --request-id request_09`:
  completed and wrote the provisional prediction artifact.
- `code/evaluation/main.py` is currently empty.
- `code/evaluation/usage_report.md` is currently empty.
- The working tree also contains implementation and task-tracker changes that
  predate this review; they were not modified.

The smoke result proves wiring for one supported case, not general financial
correctness. The 29 tests are primarily contract and provisional-policy tests;
they do not establish coverage of the full 250-request evaluation set.

## 3. Challenge coverage matrix

| Challenge capability | Current state | Review |
|---|---|---|
| Load evaluation requests | Implemented for a supplied request CSV | Exact input schema and duplicate IDs are checked. |
| Join profiles/events/options/evidence/rates | Implemented structurally | Referential checks exist, but evidence is not interpreted and all rates are loaded without request-scoped use. |
| Decimal/date normalization | Implemented | Good boundary behavior; precision/quantization policy remains unspecified. |
| Settlement-date FX | Validated but not applied | Non-home-currency events cause the slice to fail instead of being converted. |
| Blank event amounts from images | Detected as unresolved | No image extraction or reviewed fact path exists. |
| Lifecycle reconciliation | Narrow provisional case only | Only pending-to-settled same-stream links are handled. |
| Recurrence | Narrow structured inference | Requires strict cadence and at least three observations; not the full challenge policy. |
| Essential/protected/flexible spending | Not implemented | No spending-change candidates are constructed or simulated. |
| Pending debits/credits | Partial | Pending debits are reserved; pending credits are excluded and suppress inference. Other cash-state semantics remain unsupported. |
| Full payment | One sufficient case | Requires an exact fee-free full option starting on request date. |
| Partial payment | Not implemented | The decision stage raises `UnsupportedCase`. |
| Installments | Not implemented | Options are parsed, but no eligibility, schedule matching, or simulation is performed. |
| Wait/later | Not implemented | No earliest-safe-date search exists. |
| Not recommended | Not emitted by the application | Unsupported cases fail instead of producing an output row. |
| 90-day safety | Implemented for provisional timeline | It simulates the selected payment and timeline, but not the complete required candidate space. |
| Independent output validation | Partial | Schema and selected structural invariants are checked; option matching and full financial safety are not. |
| Sample benchmark | Scaffolding only | Comparators and sample isolation exist, but no runnable evaluator entry point or results are present. |
| Usage report | Interface only | Ledger types exist, but the required report file is empty and no final-run attribution exists. |

## 4. Findings

### F-01 — Critical: the pipeline cannot produce a complete evaluation output

**Evidence:** `processing.decide()` raises `UnsupportedCase` for unsafe
immediate payment and for every unsupported strategy. The application aborts
before serialization, and `main.py` reports failure rather than producing an
output row.

**Impact:** The challenge requires exactly one decision row for every request in
`dataset/requests.csv`. An unsupported-case exception is appropriate during
development, but it cannot be the final behavior for requests requiring
installments, waiting, partial payment, evidence extraction, FX, or lifecycle
resolution.

**Recommendation:** Keep fail-closed behavior internally, but add a release
policy that resolves every material unsupported case before final generation.
The final runner should process all requests only after the required strategies
and evidence paths exist; it must not convert processing failures into
`not_affordable`.

### F-02 — High: no evaluator executable or baseline results exist

**Evidence:** `code/evaluation/main.py` is empty. `comparison.py` and
`samples.py` provide library helpers, but there is no documented command that
loads all 25 samples, invokes the application, compares outputs, and writes
metrics/mismatches. `docs/tasks.md` still lists the evaluator as in progress.

**Impact:** The team cannot measure whether the vertical slice generalizes,
identify the earliest failing stage, or establish a reproducible baseline.

**Recommendation:** Implement the evaluator as a separate process boundary with
an explicit command, such as:

```text
python3 -B -m code.evaluation.main --all-samples --report <path>
```

It should create isolated input files, run the application, capture stage and
request diagnostics, compare all structured fields semantically, and write a
versioned report containing sample coverage, mismatch counts, unsupported cases,
safety failures, and configuration fingerprints.

### F-03 — High: the required usage report is empty

**Evidence:** [usage_report.md](../../code/evaluation/usage_report.md) has zero
bytes. The usage ledger can represent records, but nothing writes a report and
there are no model/cache run records.

**Impact:** The required submission artifact must summarize the final
full-dataset run, including provider/model, calls, tokens, total and average
tokens, and estimated cost. An empty file cannot satisfy this requirement.

**Recommendation:** Define a report schema and a generator now, even while
usage is zero. For a deterministic run, explicitly record zero model calls,
zero tokens, no provider/model invocation, the run identifier, request count,
and the fact that no final-run model usage occurred. Later extraction runs must
record cache-origin usage separately.

### F-04 — High: output validation is not yet challenge-complete

**Evidence:** `validation.py` checks generic structure and some method-specific
shapes, but installment outputs only require at least two payments whose sum is
at least the requested amount. It does not verify:

- exact equality to a supplied payment option;
- user method permission and `max_installment_months`;
- financing fee and total payable amount;
- balance safety for the serialized plan;
- flexible/protected category eligibility of spending changes;
- reduced amount minimums;
- `earliest_date_for_full_payment` against a forecast;
- the full request total for all plan types.

**Impact:** A future planner could emit structurally valid but financially
invalid output that passes the current validator.

**Recommendation:** Add an independent challenge-contract validator that
receives the normalized context and forecast, validates every selected option
against its source record, applies all permissions, and re-simulates the
serialized plan. Keep the current structural validator as a lower-level
schema check.

### F-05 — High: lifecycle and cash-state handling is too narrow for the dataset

**Evidence:** `_active_events()` rejects every linked lifecycle except a
pending-to-settled same-stream relationship. `build_forecast()` rejects
same-day settled events, overdue scheduled events, non-salary future credits,
foreign-currency events, and unresolved amounts.

**Impact:** The implementation correctly avoids unsafe guessing, but it cannot
handle the challenge’s required cancellations, amendments, refunds, transfers,
investment/non-cash records, settlement semantics, or FX cases.

**Recommendation:** Build the resolver as a separate deterministic component
with explicit lifecycle tests for each status and link pattern. Preserve
unresolved facts with provenance, but distinguish “unsupported during the
vertical slice” from “resolved as financially irrelevant.”

### F-06 — Medium: recurrence policy is conservative but currently over-restrictive

**Evidence:** Recurrence requires three observations, one stream key, exact
fixed intervals from a short list or matching monthly slots through day 28,
low amount deviation, and no same-day duplicates. It uses the maximum debit and
minimum salary amount.

**Impact:** This is a defensible prototype policy, but it may reject valid
recurring histories and does not yet cover month-end dates, supported cadence
variations, amendments, or variable essential expenses. It also groups by
`event_type/category/direction` without semantic lifecycle resolution.

**Recommendation:** Keep this as `vertical-slice-v1`, compare it against
alternative policies on frozen sample facts, and promote only a version with
documented boundary behavior and benchmark evidence. Do not silently broaden
the policy while implementing other features.

### F-07 — Medium: evidence routing is structurally validated but not scoped

**Evidence:** `build_context()` selects every message and image for the user,
plus request-level records. The forecast then rejects any non-empty evidence.
There is no extraction contract, relevance ranking, provenance assertion model,
or image content check beyond file existence.

**Impact:** Once extraction is added, broad user-level routing can increase
prompt size, cost, leakage between requests, and accidental use of unrelated
financial facts.

**Recommendation:** Define request/event relevance rules before model calls,
separate raw evidence from extracted assertions, cache by content/context/model/
schema version, and require deterministic acceptance checks before an assertion
can affect cash flow.

### F-08 — Medium: stage diagnostics are not yet a stable error contract

**Evidence:** `_stage()` catches `Exception`, mutates the exception with a
dynamic `failure_stage` attribute, and re-raises it. `main.py` catches only
`ValueError` and `OSError`, then prints a generic failure message without the
stage, request ID, or machine-readable diagnostic.

**Impact:** Broad interception can obscure unexpected programming failures, and
downstream evaluation cannot reliably attribute failures to loading, context,
normalization, forecast, planning, serialization, or validation.

**Recommendation:** Use a typed stage-error wrapper or structured diagnostic
record. Catch expected domain errors at the CLI boundary, preserve the original
cause, include request/stage/configuration metadata, and let unexpected
programming errors remain visibly distinct.

### F-09 — Medium: input integrity checks do not yet constitute a dataset gate

**Evidence:** The loader checks headers, uniqueness, ownership, links, image
file presence, and option count. It does not document or enforce all expected
dataset-level invariants such as request coverage against the authoritative
file, allowed request types/categories, nonnegative profile constraints,
currency code consistency, image metadata-to-file completeness, or option
request totals.

**Impact:** Corrupt or incomplete input can fail later with a less actionable
error or be interpreted under provisional assumptions.

**Recommendation:** Add a standalone preflight validator with a report of
counts, duplicates, dangling references, missing media, malformed values,
currency/rate coverage, and schedule arithmetic. Run it before any model or
planning work.

### F-10 — Low: documentation status is not synchronized with executable evidence

**Evidence:** `README.md` clearly labels the vertical slice as provisional, but
the task tracker describes evaluator work in progress while the evaluator entry
point and usage report are empty. The first review recommended a runbook and
release evidence, but the current milestone does not link artifacts proving
those gates.

**Impact:** Contributors can mistake scaffolding for a completed evaluation
milestone.

**Recommendation:** For each task, record a command, artifact path, test count,
and date. Mark evaluator and usage-report tasks complete only after a retained
run demonstrates them.

## 5. What is done well

- Application code never reads `sample_requests.csv`.
- The sample adapter projects input columns before invoking application code.
- Blank monetary values fail explicitly rather than becoming zero.
- Decimal arithmetic is used at financial boundaries.
- Dataset relationships and image paths receive structural checks.
- Output is staged in a temporary directory and moved only after validation.
- Unsupported financial reasoning is surfaced instead of disguised as a safe
  recommendation.
- The 29-test suite includes useful regressions for pending credits, duplicate
  lifecycle representations, recurrence ambiguity, output protection, and
  answer-column isolation.

## 6. Prioritized next steps

### P0 — make evaluation measurable without changing financial policy

1. Add the evaluator CLI and report format.
2. Run the two-request smoke evaluation and all 25 samples; retain mismatch and
   unsupported-case reports.
3. Generate a zero-usage report for the deterministic run.
4. Add evaluator tests and preserve the 29 application tests.
5. Add typed stage/request diagnostics and a machine-readable failure report.

### P1 — complete the deterministic financial contract

1. Separate structural validation from context-aware challenge validation.
2. Implement exact option matching and installment eligibility.
3. Implement baseline safe amount and earliest-safe-date search.
4. Implement partial payment, wait, spending-change candidates, and ranking.
5. Resolve lifecycle/cash-state semantics and settlement-date FX.
6. Add independent balance simulations for every serialized plan.

### P2 — add evidence and release controls

1. Implement reviewed image/message extraction with provenance and cache versioning.
2. Add prompt-injection/untrusted-evidence fixtures.
3. Add dataset preflight and full output release gates.
4. Generate the final usage report from the exact full-dataset run.
5. Package and inspect `code.zip`, transcript, output, manifest, and checksums.

## 7. Recommended acceptance criteria for the next milestone

- [ ] `code/evaluation/main.py` has a documented executable command.
- [ ] All 25 solved samples can be selected or run in one command.
- [ ] The evaluator reports per-field matches, unsupported cases, and failures by
  pipeline stage.
- [ ] The evaluator cannot pass sample expected outputs into application code.
- [ ] The deterministic run emits a nonempty, schema-defined usage report.
- [ ] The report distinguishes zero current model calls from unavailable model
  cost data.
- [ ] All 29 existing tests remain green and evaluator tests are added.
- [ ] No evaluator result is described as financial accuracy until unsupported
  cases and validation gaps are separately reported.
- [ ] The next review can inspect retained baseline artifacts rather than only
  source scaffolding.
