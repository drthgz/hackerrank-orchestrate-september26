# Documentation Review 08: Forecast-Capacity Modeling Phase

**Repository:** HackerRank Orchestrate - Buy or Wait?  
**Review date:** 2026-09-13  
**Scope:** Updated deterministic forecast/capacity modeling, final 25-sample
benchmark, planning outputs, and phase documentation. This review is advisory;
no code or existing documentation was changed.

## 1. Executive assessment

This phase is a major readiness milestone. The pipeline now processes the full
25/25 solved-sample benchmark with **0 unsupported and 0 failed requests**.
That is the first point at which aggregate metrics meaningfully describe the
implemented system rather than a mixture of predictions and missing coverage.

The reported error reductions are substantial: MAE approximately **998k to
107k**, and median absolute error approximately **10.9k to 5.1k**. Status,
payment-method, and spending-change accuracy also improved without reported
regressions. The remaining issues are appropriately classified as forecast
construction/capacity policy errors rather than missing evaluator, extraction,
or pipeline architecture.

The benchmark artifact confirms full coverage and zero failures, but the
repository metrics file does not currently include the reported MAE or median
absolute error fields. That is a documentation/evaluation reproducibility gap:
the headline improvements should be generated and retained by the evaluator,
not only communicated externally.

**Current maturity:** strong end-to-end development benchmark; remaining work is
primarily forecast calibration, independent release validation, usage reporting,
and final full-dataset production.

## 2. Results reviewed

Artifact: `artifacts/evaluation/forecast-capacity-v3-final-verified/`

| Measure | Result |
|---|---:|
| Solved samples selected | 25 |
| Processed | 25 |
| Unsupported | 0 |
| Failed | 0 |
| Missing prediction fields | 0 |
| Fully matching structured rows | 1 |
| Comparable structured mismatches | 88 |
| Status matches | 10/25 |
| Payment-method matches | 11/25 |
| Spending-change matches | 22/25 |
| Model calls/tokens/cost | 0/0/0 |

The artifact reports complete coverage and no stage failures. It also shows
that amount-safe-to-pay remains the weakest field at 1/25 exact matches, while
spending-change output is comparatively strong at 22/25.

The reported MAE and median absolute error improvements are important, but they
should be persisted in `metrics.json` with explicit definitions, units,
outlier handling, and denominators.

## 3. What was completed well

### 3.1 Full solved-sample coverage

Moving from partial processing to 25/25 processed requests is the most important
phase outcome. It proves that extraction replay, reconciliation, stream
projection, forecasting, and planning now compose across the solved benchmark.

### 3.2 Failures are now diagnosable as forecast decisions

There are no unsupported or failed requests in the final artifact. Remaining
differences are serialized predictions that can be compared field-by-field,
rather than hidden behind architectural exceptions. This enables targeted
forecast-policy analysis.

### 3.3 Safety-oriented modeling was retained

The phase did not reintroduce the earlier unsafe `request_05` recommendation.
Forecast changes improved capacity modeling while preserving deterministic
simulation and the minimum-balance constraint.

### 3.4 Decision-field accuracy improved

Status, method, and spending-change metrics improved alongside capacity
calibration. This indicates that the changes affected downstream decisions,
not merely a single numeric field.

### 3.5 Evidence remained frozen and replayable

The metadata retains dataset/source fingerprints and cached extraction mode.
That makes the forecast comparison more meaningful because extraction variance
is not mixed into this phase’s result.

## 4. Findings

### F-01 — High: headline error metrics are not retained in the evaluator artifact

The final `metrics.json` contains field-level exact-match metrics but not the
reported MAE or median absolute error. Without persisted error metrics, a
reviewer cannot reproduce the claimed 998k-to-107k and 10.9k-to-5.1k changes
from the authoritative run directory.

**Recommendation:** Add to `metrics.json`:

```text
amount_error_metrics:
  comparable_predictions
  mean_absolute_error
  median_absolute_error
  max_absolute_error
  p90_absolute_error
  currency/scale assumptions
```

Also retain a per-request numeric error table and identify whether metrics are
computed over all 25 predictions or only valid/comparable rows.

### F-02 — High: exact amount accuracy remains 1/25 despite lower aggregate error

The lower MAE is a meaningful improvement, but only one request has an exact
`amount_safe_to_pay` match. A large reduction in average error can coexist
with materially unsafe overprediction on a few requests.

**Recommendation:** Add safety-oriented error buckets:

- overprediction versus expected safe amount;
- underprediction;
- zero versus positive capacity;
- status/method inconsistency;
- minimum-balance safety violations;
- absolute and relative error bands.

Review the largest overpredictions first, as the task is safety-sensitive.

### F-03 — High: the forecast/capacity contract needs explicit versioned semantics

The new policy is versioned as `forecast-capacity-v3`, but the documentation
does not yet fully specify how confirmed dated income, behavior spending,
horizon boundaries, pending holds, same-day ordering, and opening balance
interact in the capacity calculation.

**Recommendation:** Add a capacity policy contract describing:

1. opening snapshot and historical replay assumptions;
2. exact horizon inclusion;
3. event/payment ordering on the same day;
4. treatment of confirmed future income;
5. behavior-stream projected amounts and contingency reserves;
6. optional spending-change exclusion from baseline capacity;
7. Decimal rounding and cent search semantics.

Each rule should link to a regression fixture and a forecast trace.

### F-04 — High: “no regressions” needs a formal comparison gate

The user reports no regressions, but the final artifact alone does not identify
which previous benchmark fields improved, stayed equal, or regressed relative
to `forecast-capacity-v2` and earlier verified runs.

**Recommendation:** Add a comparison report keyed by request and field:

```text
baseline run -> candidate run -> changed fields -> safety outcome
```

Require zero newly unsafe plans and zero newly failed validations before
accepting a forecast policy. Accuracy regressions may be acceptable when a
safety correction is intentional, but must be documented.

### F-05 — High: full solved-sample coverage is not full challenge coverage

The 25/25 result covers solved examples, not the 250 evaluation requests in
`dataset/requests.csv`. It is a major development milestone but not evidence
that the final output generator handles the hidden evaluation set.

**Recommendation:** Add a separate full-dataset release run that produces root
`output.csv`, validates exactly one row per evaluation request, records all
request outcomes, and retains a full-run manifest. Keep sample benchmark
metrics separate from release metrics.

### F-06 — Medium: planning validation remains structurally ahead of independent safety validation

The benchmark reports `validation=passed`, but the review of previous phases
identified that the current validator does not independently re-simulate every
serialized plan against resolved context for all strategy types.

**Recommendation:** Make post-serialization context-aware safety validation a
release gate. Verify exact installment option matching, partial-payment totals,
deadline, flexible-only changes, baseline amount semantics, and minimum balance
from the serialized CSV—not only from in-memory candidates.

### F-07 — Medium: spending-change accuracy is strong but requires adversarial safety checks

Spending-change matches are 22/25, which is encouraging. However, exact field
matching does not prove that all actions are eligible under protected
categories, flexibility, minimum amounts, effective dates, and stream source
lineage.

**Recommendation:** Report action validity independently from action-label
accuracy. Add negative fixtures for protected events, non-flexible events,
duplicate stop/reduce targets, and changes that only make the plan safe after
the allowed completion date.

### F-08 — Medium: explanation quality is still not evaluated semantically

All 25 explanation comparisons are diagnostic mismatches. Exact prose equality
is not an appropriate primary metric, but the system should still demonstrate
that explanations accurately reflect selected method, plan, reserve, and
blocking facts.

**Recommendation:** Add deterministic explanation consistency checks against
the serialized decision, or a structured explanation payload from which prose
is rendered. Never allow unsupported facts or claims not present in the
validated plan.

### F-09 — Low: usage-report completion remains a release obligation

The phase uses cached extraction with zero model calls in the verified run.
That is useful evidence, but the required submitted Markdown usage report
still needs to describe final-run replay usage and originating extraction cost.

**Recommendation:** Generate the report from the authoritative run manifest,
including cache hits, origin calls/tokens/cost, current-run calls/tokens/cost,
averages per request, and pricing basis.

## 5. Phase verdict

| Dimension | Verdict |
|---|---|
| End-to-end sample coverage | **Excellent milestone** — 25/25 processed |
| Failure elimination | **Excellent** — 0 unsupported, 0 failed |
| Aggregate capacity accuracy | **Strong improvement** — reported MAE and median error sharply reduced |
| Exact safe-amount accuracy | **Still weak** — 1/25 exact |
| Decision quality | **Improved** — status/method/spending changes better |
| Safety posture | **Promising** — no known regression reported; needs independent release simulation |
| Reproducibility | **Good foundation** — frozen evidence and fingerprints |
| Submission readiness | **Not yet** — full 250-request run and release artifacts remain |

## 6. Prioritized next steps

### P0 — make the improvement measurable and safety-auditable

- Persist MAE, median, p90, max, over/underprediction, and error-band metrics.
- Add a v2-to-v3 no-regression comparison artifact.
- Investigate the largest safe-amount overpredictions.
- Add independent post-serialization financial safety validation.

### P1 — finalize forecast policy

- Document and fixture opening balance, horizon, same-day ordering, confirmed
  income, pending holds, behavior reserve, and rounding semantics.
- Validate the remaining income-continuation and cadence/horizon clusters.
- Re-run the 25-sample benchmark with frozen extraction facts after each policy
  change.

### P2 — release preparation

- Run all 250 evaluation requests with cached evidence and retain a manifest.
- Generate the required nonempty usage report.
- Validate root `output.csv` coverage, schema, plans, actions, and safety.
- Package code, output, transcript, usage report, and checksums without secrets.

## 7. Recommended next-milestone acceptance criteria

- [ ] `metrics.json` includes reproducible MAE and median absolute error.
- [ ] A no-regression comparison against the previous forecast policy is retained.
- [ ] Largest overpredicted safe amounts have generalized causes and tests.
- [ ] Serialized-output safety validation independently passes for all 25 samples.
- [ ] Forecast policy semantics are documented and linked to fixtures/traces.
- [ ] Full 250-request output generation completes without unsupported/failed
  processing or fabricated fallbacks.
- [ ] Final usage report distinguishes cached replay from originating model cost.
