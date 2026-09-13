# Documentation Review 09: Final Deterministic Tuning Pass

**Repository:** HackerRank Orchestrate - Buy or Wait?  
**Review date:** 2026-09-13  
**Scope:** The final targeted tuning pass, the `safety-pass-v1-fixed-streams`
benchmark, regression tests, and release-readiness implications. This review
does not modify production code or existing documentation.

## 1. Executive assessment

This was a sensible final safety-oriented tuning pass rather than a broad
feature expansion. The change requires every event in a behavior stream to
explicitly declare a flexible policy before using a mean expense estimate.
Protected or non-explicitly-flexible expenses now use the conservative maximum
observed amount. This is a defensible general rule and directly addresses the
previous over-capacity risk in variable spending.

The new run confirms the important operational properties:

- **25/25 selected requests processed**
- **0 unsupported**
- **0 failed**
- **106 tests pass**
- **No prediction fields are missing**

However, the latest benchmark is not an accuracy improvement over the prior
`forecast-capacity-v3-final-verified` run on exact structured metrics:
comparable mismatches increased from **88 to 90**, affordability-status
matches decreased from **10/25 to 9/25**, and payment-method matches decreased
from **11/25 to 10/25**. Safe amounts became more conservative in the inspected
overprediction cases, but exact `amount_safe_to_pay` accuracy remained **1/25**.

**Verdict:** The pass improves safety posture and reduces selected
overpredictions, but should be treated as a conservative policy amendment, not
as a benchmark accuracy win. It is appropriate to stop sample-specific tuning
and proceed to a production dry run only with explicit safety and regression
gates.

## 2. Evidence reviewed

Primary artifact:
`artifacts/evaluation/safety-pass-v1-fixed-streams/`

Baseline comparison:
`artifacts/evaluation/forecast-capacity-v3-final-verified/`

Implementation change:
`code/buy_or_wait/streams.py`

Related decision and task records:
`docs/decisions.md` and `docs/tasks.md`

Regression command:

```text
python3 -B -m unittest discover -s tests -v
```

Result: **106 tests passed**.

## 3. Benchmark comparison

| Measure | Previous v3 verified | Safety pass | Change |
|---|---:|---:|---:|
| Selected | 25 | 25 | — |
| Processed | 25 | 25 | — |
| Unsupported | 0 | 0 | — |
| Failed | 0 | 0 | — |
| Missing prediction fields | 0 | 0 | — |
| Fully matching structured rows | 1 | 1 | — |
| Comparable structured mismatches | 88 | 90 | +2 |
| Affordability status | 10/25 | 9/25 | -1 |
| Recommended method | 11/25 | 10/25 | -1 |
| Payment plan | 10/25 | 10/25 | — |
| Earliest full-payment date | 8/25 | 8/25 | — |
| Spending changes | 22/25 | 22/25 | — |
| Safe amount | 1/25 | 1/25 | — |

The pass therefore preserved full coverage and strong spending-change accuracy,
but caused small exact-match regressions in downstream decision fields.

## 4. What was completed well

### 4.1 The policy change is generalized rather than request-specific

The implementation gates the non-conservative mean estimator on explicit
flexibility metadata across the stream. It does not add request IDs,
expected-output checks, or hidden sample labels. This is consistent with the
challenge prohibition on hardcoded labels and with industrial data-policy
practice.

### 4.2 Safety is favored when flexibility is not evidenced

The rule correctly distinguishes “not protected” from “known flexible.” A
non-protected event is not automatically reducible or stoppable. Using the
maximum observed expense in that case is conservative and avoids treating
ordinary discretionary-looking activity as safely cancellable.

### 4.3 Coverage and reliability were preserved

The policy did not create unsupported or failed requests. The evaluator still
produces complete per-request artifacts and all prediction fields are present.

### 4.4 The team stopped before overfitting further

The task record explicitly marks residual differences as lacking a
repository-supported general rule. That is the correct stopping discipline for
a small solved benchmark and is preferable to adding sample-specific patches.

## 5. Findings

### F-01 — High: the latest pass is a safety adjustment, not an accuracy improvement

The new artifact has 90 comparable structured mismatches versus 88 previously,
with one fewer status match and one fewer method match. This should be stated
explicitly in milestone reporting so “final tuning” is not interpreted as a
globally better predictor.

**Recommendation:** Maintain a promotion table with separate gates for:

- coverage and failure rate;
- safety violations and overprediction;
- exact structured accuracy;
- aggregate monetary error;
- decision-field accuracy.

Promote the new policy if its safety benefit is material and documented, even
when exact accuracy declines, but do not label it an accuracy win.

### F-02 — High: conservative amount reduction needs a direct safety metric

The inspected cases show lower predicted capacity for requests 03, 20, and 21,
but exact amount accuracy is still 1/25. Exact equality is not sufficient to
judge financial safety, and lower amounts are not automatically correct if
they cause an unnecessary `not_recommended` decision or miss a permitted plan.

**Recommendation:** Persist per-request:

- expected amount and predicted amount;
- signed error and absolute error;
- overprediction flag;
- minimum projected balance;
- minimum-balance violation flag;
- selected plan and whether it completes by deadline.

Report overprediction rate and worst-case overprediction separately from MAE.

### F-03 — High: “all events explicitly flexible” may be too strict for mixed streams

The new condition uses `all(...)` across a behavior stream. This is safe, but
it can collapse a mixed stream to the maximum estimator because one historical
event lacks metadata. That may explain the downstream status/method regressions
and can understate safe capacity.

**Recommendation:** Before changing the rule, add fixtures for:

- all events flexible;
- one missing flexibility value;
- mixed reducible and stoppable values;
- protected plus flexible category boundaries;
- a later explicit amendment that changes flexibility.

Document whether missing metadata means “non-flexible,” “unknown,” or “data
quality failure.” Keep the conservative default, but measure its impact.

### F-04 — Medium: the policy version and benchmark comparison should be linked

The artifact records `forecast-capacity-v3` and `recurring-streams-v2`, while
the run is named `safety-pass-v1-fixed-streams`. This is useful provenance, but
the policy amendment is not represented as a distinct forecast policy version.

**Recommendation:** Use a unique policy/configuration identifier for every
benchmarkable behavior change, or record an explicit amendment hash in
metadata. The before/after artifact should identify the exact source and policy
configuration used for both runs.

### F-05 — Medium: the before/after diagnostic is not yet a release gate

The task record says a 25-row before/after table was added, but the authoritative
evaluation artifact does not expose a machine-readable promotion decision or a
formal no-regression result.

**Recommendation:** Generate a comparison artifact with one row per request and
field, plus columns for safety outcome, plan eligibility, and regression class.
Require review of every newly changed decision, not just the aggregate counts.

### F-06 — Medium: full solved-sample coverage still does not prove hidden-set readiness

The run covers the 25 solved samples. It does not establish behavior over the
full 250-request evaluation input or prove that unseen flexibility metadata,
mixed streams, installment boundaries, and evidence amendments are handled.

**Recommendation:** Run the production dry run using frozen cached extraction,
validate one output row per evaluation request, and preserve a manifest without
using expected sample answers in application execution.

### F-07 — Medium: release safety must be checked after serialization

The benchmark reports structural validation success, but structural validity
does not prove that serialized payment plans preserve minimum balance, deadline,
option identity, or spending-change eligibility.

**Recommendation:** Re-read the generated CSV and independently re-simulate
every plan from resolved context. Make this a release blocker for any
minimum-balance violation, malformed plan, invalid action, or unsupported
payment option.

### F-08 — Low: error headline metrics remain incompletely persisted

The prior review identified that MAE and median absolute error were reported
externally but not retained in the authoritative metrics artifact. The latest
run still exposes field exact-match metrics but not those aggregate monetary
statistics.

**Recommendation:** Persist MAE, median, p90, maximum, signed bias, and
overprediction rate with units, denominator, currency assumptions, and policy
version.

## 6. Industrial-standard assessment

| Area | Assessment |
|---|---|
| Change isolation | **Good** — narrow stream-policy change |
| Determinism | **Good** — no new model calls or nondeterministic dependency |
| Safety default | **Good** — unknown flexibility does not grant permission to reduce |
| Test discipline | **Good** — 106 tests pass |
| Regression analysis | **Partial** — aggregate comparison exists, formal promotion gate does not |
| Observability | **Good foundation** — request artifacts exist; safety metrics need expansion |
| Reproducibility | **Good** — fingerprints and policy metadata retained |
| Release readiness | **Incomplete** — production dry run and independent serialized safety checks remain |

## 7. Recommended next steps

### P0 — before production dry run

1. Preserve the safety-pass artifact and do not overwrite the prior baseline.
2. Generate a machine-readable before/after comparison with safety outcomes.
3. Add overprediction and minimum-balance violation metrics.
4. Re-run independent post-serialization validation.
5. Confirm the `all-flexible` rule with mixed-metadata fixtures.

### P1 — during production dry run

1. Use cached extraction only and record cache-origin usage separately.
2. Generate exactly one valid row for every evaluation request.
3. Retain request-level diagnostics, policy hashes, source fingerprints, and
   validation results.
4. Do not tune against hidden/organizer-only labels.

### P2 — before submission

1. Generate the required nonempty `code/evaluation/usage_report.md`.
2. Resolve or explicitly document opening-balance timing, horizon boundaries,
   same-day ordering, installment duration, rounding, and tie-break semantics.
3. Package `code.zip`, `output.csv`, transcript, usage report, and checksums.

## 8. Acceptance criteria for this phase

- [x] All 25 solved samples process without unsupported or failed outcomes.
- [x] No new request-specific rules or expected-answer access were introduced.
- [x] Regression suite passes: 106 tests.
- [x] Flexibility policy is conservative when metadata is missing.
- [ ] Safety metrics include overprediction and minimum-balance violations.
- [ ] A formal v3-to-safety-pass promotion comparison is retained.
- [ ] Serialized output is independently re-simulated.
- [ ] Full 250-request production dry run is complete.
- [ ] Final usage report is generated and nonempty.

