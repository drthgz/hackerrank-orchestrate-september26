# Documentation Review 03: Evaluation Harness Phase

**Repository:** HackerRank Orchestrate - Buy or Wait?  
**Review date:** 2026-09-13  
**Scope:** Completed sample-evaluation harness, baseline artifacts, evaluator
documentation, and reported test results. This review is advisory; no code or
existing documentation was changed.

## 1. Executive assessment

The evaluation harness milestone is complete and is a meaningful improvement
over the original vertical slice. It now provides repeatable selection,
input/answer isolation, per-request failure handling, semantic field comparison,
run metadata, source/dataset fingerprints, and immutable artifact directories.
The reported baseline is appropriately conservative: it does not turn
unsupported requests into fabricated financial predictions and clearly
separates all-selected accuracy from processed-only accuracy.

The harness is suitable for guiding deterministic-engine development. It is not
yet a final submission evaluator because it evaluates the 25 solved samples
rather than the 250-request output contract, and its current usage artifact is
a development ledger rather than the required final full-dataset usage report.
The baseline also demonstrates that the financial engine, not the evaluator, is
now the dominant limitation.

**Current maturity:** strong development evaluation harness; financial engine
coverage remains far below challenge coverage.

## 2. Results reviewed

The reported commands and baseline artifacts establish:

| Run | Selected | Processed | Unsupported | Failed | Fully matching structured rows |
|---|---:|---:|---:|---:|---:|
| `request_09` | 1 | 1 | 0 | 0 | 1 |
| `request_09` + `request_01` | 2 | 1 | 1 | 0 | 1 |
| smoke subset | 2 | 1 | 1 | 0 | 1 |
| all solved samples / `baseline-v1` | 25 | 2 | 21 | 2 | 1 |

The full baseline reports:

- 1/25 fully matching structured rows: **4% overall**.
- 1/2 fully matching structured rows among processed predictions: **50%**.
- 5 comparable financial-field mismatches.
- 138 missing financial fields from unsupported/failed requests.
- 18 uninterpreted-evidence blockers.
- 1 linked-lifecycle blocker.
- 1 variable-salary recurrence blocker.
- 1 unsupported FX blocker.
- 2 normalization failures for `direction=non_cash`.
- Zero model calls, zero tokens, zero cache activity, and zero reported cost.

These are valid internal development metrics, not an official HackerRank score.
The distinction is correctly documented.

## 3. What the harness does well

### 3.1 Prevents sample-label leakage

The evaluator separates request input columns from expected answers before
writing per-request input files. The application receives only the input CSV,
dataset path, policy, and output path. The application does not import
evaluation modules or read `sample_requests.csv`.

This is an important integrity property and should remain a release-gated test.

### 3.2 Treats unsupported results honestly

Unsupported requests are recorded with an outcome, stage, exception type, and
diagnostic. Missing predictions are counted as unmatched for all-selected
metrics instead of being converted into `not_affordable`. This is safer and
more informative than success-shaped fallback output.

### 3.3 Uses semantic comparisons for structured fields

Decimal amounts compare numerically, dates compare as dates, plans preserve
payment count and chronology, and spending changes normalize action ordering.
Explanation text is explicitly diagnostic-only. This avoids overstating exact
prose equality as financial accuracy.

### 3.4 Preserves reproducibility evidence

Each run records the selected requests, policy configuration/version, local Git
revision, source hash, dataset hash, extraction mode, and artifact directory.
Run directories are unique and are not overwritten. This is a good foundation
for comparing policy changes on frozen facts.

### 3.5 Produces useful failure localization

The harness distinguishes unsupported from failed requests and records observed
stages such as `forecast` and `normalization`. It also correctly labels field
mismatches as causally unknown rather than pretending that comparison alone
proves a forecasting bug.

## 4. Findings

### F-01 — Critical: the harness evaluates solved samples, not the required final dataset

The `--all` command means all 25 rows in `sample_requests.csv`; it does not
mean all 250 evaluation requests in `requests.csv`. This is correctly described
in the evaluator README but can be confused with a production release run.

**Impact:** A passing or improving sample benchmark cannot prove complete output
coverage for the actual submission. The current baseline has no evidence that
the final runner can generate 250 rows.

**Recommendation:** Keep `--all` explicitly named `--all-samples` or document
the distinction prominently. Add a separate release evaluator/validator that:

1. reads `dataset/requests.csv`;
2. generates exactly one row per request;
3. validates the serialized root `output.csv`;
4. checks all challenge invariants independently; and
5. records a full-dataset run manifest.

### F-02 — High: processed-only accuracy is statistically fragile

Only two of 25 requests were processed. Therefore 50% processed-only accuracy
is based on two observations and should not be used as evidence of a reliable
model or policy.

**Recommendation:** Always print the processed denominator beside every
processed-only metric, as the harness does conceptually. Add a warning when the
processed fraction is below a documented threshold, for example 80% for a
benchmark milestone. Report coverage separately from correctness:

```text
coverage = processed / selected
conditional_accuracy = matches / processed
end_to_end_accuracy = matches / selected
```

The report should make coverage the primary milestone metric until the engine
handles the full sample set.

### F-03 — High: the baseline exposes a material false-positive financial result

`request_05` processed but matched only 1/6 structured fields. The safe amount
was reported as 15488 while the sample expected 737, and status, method, plan,
and earliest date also differed. The harness correctly states that comparison
does not prove the causal stage.

**Impact:** This is a safety-significant discrepancy, not merely a benchmark
miss. A financial engine should not advance based on aggregate metrics while a
processed case can materially overstate safe capacity.

**Recommendation:** Treat request_05 as a diagnostic fixture, not a label-fitting
target. Trace the complete opening balance, future cash entries, minimum-balance
reserve, request payment, and same-day ordering. Add a balance-trace artifact
and a regression test for the generalized accounting cause once identified.
Do not add a request-ID special case.

### F-04 — High: failure taxonomy currently conflates unsupported product scope and data defects

The baseline records 21 `UnsupportedCase` results and two normalization
failures, but the report does not yet provide a normalized blocker taxonomy
across:

- missing capability (evidence extraction, installments, planning);
- unresolved policy;
- invalid or unsupported source data;
- implementation defect;
- intentionally excluded case.

The two `non_cash` normalization failures are especially important: they appear
to be source-domain records that should likely be represented as non-cash rather
than rejected as an invalid debit/credit direction.

**Recommendation:** Add a stable blocker code and severity to each result, for
example `EVIDENCE_UNRESOLVED`, `LIFECYCLE_UNSUPPORTED`,
`NON_CASH_EVENT`, `FX_UNSUPPORTED`, and `RECURRENCE_AMBIGUOUS`. Keep the human
diagnostic, but aggregate by blocker code and distinguish data-invalid from
feature-not-yet-implemented.

### F-05 — High: evaluator metrics are not yet safety metrics

The harness compares expected fields and validates structural output, but the
current validation path does not independently prove minimum-balance safety,
exact supplied-option matching, flexible-only spending changes, or complete
payment totals for all future methods.

**Impact:** A prediction can match the sample answer or pass structural
validation without proving that the plan is financially safe under the source
records.

**Recommendation:** Add context-aware release validation as a separate stage.
For every processed prediction, re-read the serialized row, reconstruct its
payments and changes, resolve the referenced option/events, and independently
simulate the balance. Report safety-pass/fail separately from answer-match.

### F-06 — Medium: mismatch accounting is useful but should be split into coverage and comparison tables

The 145 total mismatch rows include missing fields for unsupported/failed
requests and two explanation diagnostics. This is transparent, but a single
total is easy to misread as 145 independent financial errors.

**Recommendation:** Retain the current total for artifact accounting, but make
the primary report tables:

1. request coverage/outcomes;
2. comparable predictions and field accuracy;
3. missing-prediction fields;
4. diagnostic prose/identifier differences;
5. safety-validation failures.

Add an explicit `comparable_requests` count and `comparable_field_count` to
`metrics.json`.

### F-07 — Medium: the zero-usage ledger is truthful but not yet the required usage report

The current `usage.json` correctly records no model calls, tokens, cache hits,
or cost. However, the challenge requires
`evaluation/usage_report.md` in the submitted code package to summarize the
final full-dataset run, including total and average tokens per request and
estimated cost.

**Recommendation:** Keep the machine-readable ledger and generate a Markdown
report from it. Include run ID, request count, provider/model records (or an
explicit “no model invoked”), total and average input/output/total tokens per
request, retries, cache origin, pricing basis, and cost. For zero calls, use
explicit zero values and state that the run was deterministic rather than
leaving the submission file empty.

### F-08 — Medium: run metadata fingerprints source and data, but not all release inputs

The metadata records Git revision, Python source hash, configuration hash, and
dataset hash. It does not clearly fingerprint the evaluator documentation,
runtime/dependency versions, operating-system context, or the exact command
line. The current standard-library-only claim reduces risk, but reproducibility
would still benefit from these fields.

**Recommendation:** Add Python version, platform, command-line selection,
policy-config file hash when supplied, evaluator version, and dependency
manifest/hash. Keep secrets and sensitive environment values out of metadata.

### F-09 — Medium: per-request artifacts need a stronger manifest and retention contract

The run emits predictions, metrics, mismatches, request results, usage, and
metadata, which is good. The documentation does not define required file
checksums, schema versions, artifact retention, or how a run is promoted as the
baseline.

**Recommendation:** Add `manifest.json` containing artifact paths, byte sizes,
SHA-256 hashes, schema versions, and the run status. Define which artifacts are
retained for every milestone and which run ID is authoritative.

### F-10 — Low: policy comparison support is present but not yet demonstrated

`--policy-config` allows explicit forecast-policy overrides, and metadata hashes
the resulting configuration. No reported comparison run demonstrates that two
policies were evaluated on identical selected facts with a useful diff.

**Recommendation:** Add a policy-comparison command/report that pairs runs by
selection and dataset hash, summarizes changed outcomes/coverage/field matches,
and warns if source or extraction fingerprints differ. This will reduce
overfitting risk during recurrence-policy work.

## 5. Interpretation of the baseline

The baseline should be read as follows:

1. **Harness correctness:** good enough to support the next engineering phase;
   isolation and artifact behavior are credible.
2. **Pipeline coverage:** 2/25 sample requests processed, so coverage is the
   immediate bottleneck.
3. **Financial correctness:** one complete match and one major mismatch are too
   few processed cases to support conclusions.
4. **Evidence capability:** absent; 18 cases explicitly wait for extraction and
   evidence resolution.
5. **Data-model capability:** incomplete; lifecycle, non-cash, variable income,
   and FX semantics remain unresolved.
6. **Submission readiness:** not ready; no full 250-request output or final
   usage report has been demonstrated.

## 6. Prioritized next steps

### P0 — before tuning financial policies

- Add blocker taxonomy and coverage-first reporting.
- Investigate request_05 with a complete balance trace and regression fixture.
- Correctly classify/handle non-cash investment events without counting them as
  available cash.
- Add context-aware independent safety validation.
- Generate a nonempty schema-compliant Markdown usage report from the zero-call
  ledger.

### P1 — deterministic engine expansion

- Implement lifecycle resolution and conflict precedence.
- Implement settlement-date FX conversion.
- Implement baseline safe amount and earliest-safe-date search.
- Implement partial payment, installment matching, waiting, and ranking.
- Implement eligible flexible spending changes and re-simulation.
- Re-run all 25 samples after each coherent policy change and preserve run
  comparisons.

### P2 — evidence and release

- Add reviewed image/message extraction with provenance and cache versioning.
- Add prompt-injection and unresolved-evidence tests.
- Add a 250-request release runner and serialized-output validator.
- Record final run metadata, artifact manifest, usage report, output coverage,
  and package inspection.

## 7. Recommended next-milestone acceptance criteria

- [ ] All 46 current tests remain green, including 17 evaluator tests.
- [ ] Baseline artifacts remain immutable and can be regenerated with a new run
  ID.
- [ ] Metrics report coverage, comparable requests, conditional accuracy, and
  end-to-end accuracy separately.
- [ ] Every unsupported/failed result has a stable blocker code and stage.
- [ ] Request_05 has a retained diagnostic balance trace; no ID-specific fix is
  used.
- [ ] Non-cash events are represented safely and tested independently of cash
  debits/credits.
- [ ] Serialized predictions receive context-aware safety validation.
- [ ] `evaluation/usage_report.md` is generated from the exact authoritative run.
- [ ] A separate full-dataset command validates 250 output rows without using
  sample answers.
- [ ] Policy comparisons include matching dataset/source/configuration
  fingerprints.
