# Documentation Review 10: 250-Request Production Dry Run

**Repository:** HackerRank Orchestrate - Buy or Wait?  
**Review date:** 2026-09-13  
**Scope:** `blocker-pass-v4-final-cached` production dry run, strict
read-back audit, submission contract, and Hackathon readiness. This review
does not modify production code or existing documentation.

## 1. Executive assessment

The production dry run reached the most important coverage milestone:

- **250/250 requests generated**
- **0 unsupported**
- **0 failed**
- **250 unique request IDs**
- **Exact required output columns**
- **Strict read-back validation passed**
- **No supplied-option or spending-change validation errors**
- **Cached replay used 0 new model calls**

This demonstrates that the pipeline can produce a complete, structurally valid
250-row artifact from the full evaluation input. The application is therefore
operationally ready for a final run.

It is **not yet submission-ready as a package**. The validated output is still
under `artifacts/production/blocker-pass-v4-final-cached/output.csv`, not at
the required repository-root `output.csv`. `code/evaluation/usage_report.md`
is empty, and no `code.zip` or final chat transcript artifact is present.
The usage report is explicitly required to describe the exact full run that
produced the submitted output.

The dry run also proves structural completeness, not financial correctness.
The 25-sample benchmark still has only 1/25 fully matching structured rows and
weak exact safe-amount accuracy. Those limitations should be understood as
prediction-quality risk rather than a release-blocking processing failure.

**Verdict:** Ready to perform the final production generation and packaging
steps; **not ready to submit until the release artifacts below are completed**.

## 2. Evidence reviewed

Primary production artifact:
`artifacts/production/blocker-pass-v4-final-cached/`

Files reviewed:

- `output.csv`
- `summary.json`
- `strict_readback_audit.json`
- `metadata.json`
- `usage.json`

Related acceptance records:

- `docs/tasks.md`
- `README.md`
- `code/evaluation/usage_report.md`

## 3. Production-run results

| Check | Result | Assessment |
|---|---:|---|
| Requests selected | 250 | Complete |
| Rows generated | 250 | Complete |
| Unique request IDs | 250 | Complete |
| Request-ID set matches dataset | Yes | Complete |
| Required columns/order | Exact | Complete |
| Unsupported requests | 0 | Complete |
| Failed requests | 0 | Complete |
| Strict read-back validation | Passed | Complete |
| Supplied payment-option errors | 0 | Complete |
| Spending-change errors | 0 | Complete |
| Current-run model calls | 0 | Complete cached replay |
| Current-run tokens/cost | 0/0 | Must be attributed carefully |

The output has 250 rows plus a header. All eight required fields are populated
for every row; an empty `earliest_date_for_full_payment` is valid when no safe
full payment exists within the forecast period.

## 4. Hackathon criteria assessment

| Hackathon requirement | Status | Review |
|---|---|---|
| Runnable from terminal | **Met** | Existing documented commands and production runner are present |
| Reads provided `dataset/` files | **Met** | Metadata points to the repository dataset |
| One prediction per evaluation request | **Met in artifact** | 250/250 and exact ID set |
| Exact output columns/order | **Met in artifact** | Strict read-back passed |
| Amount bounds and output shape | **Met by strict audit** | Preserve the audit with the final output |
| Installments match supplied options | **Met by strict audit** | No supplied-option errors |
| Spending changes use permitted actions | **Met by current audit** | No action errors reported |
| Deterministic/replayable behavior | **Met for cached run** | Frozen cache and policy metadata retained |
| No organizer-only files/hardcoded labels | **Appears met** | No evidence of answer leakage in reviewed boundary |
| Secrets from environment only | **Review before package** | Confirm package excludes credentials and cache secrets |
| `evaluation/usage_report.md` | **Not met** | File is empty |
| Root `output.csv` | **Not met** | Only artifact output exists |
| `code.zip` | **Not met** | Package has not been created |
| Chat transcript | **Not met/ not evidenced** | Repository log exists but submission transcript artifact is absent |

## 5. Findings

### F-01 — Critical for submission: final output is not at the required path

The dry-run output is valid at:

`artifacts/production/blocker-pass-v4-final-cached/output.csv`

The Hackathon contract requires the completed predictions at repository root:

`output.csv`

Do not manually edit or reformat the file during copying. Generate or copy the
exact validated artifact, then run the same strict checks against the root file.

### F-02 — Critical for submission: required usage report is empty

`code/evaluation/usage_report.md` is currently zero bytes. The contract
requires provider/model, calls, input/output tokens, total and average tokens
per request, and estimated total/per-request cost for the final full-dataset
run that produced `output.csv`.

The production run used cached replay, so the report must distinguish:

- current run: 0 calls, 0 input tokens, 0 output tokens, 0 current cost;
- cache hits and cache misses;
- originating live extraction run: 156 calls and the measured cost, if that
  is the run whose evidence created the cache;
- whether the submission reports current-run cost, origin cost, or both.

Do not describe cached replay as though the evidence had never incurred an
originating extraction cost.

### F-03 — Critical for submission: packaging artifacts are absent

No root `code.zip` or final transcript artifact was found. The submission
contract requires `code.zip`, completed `output.csv`, and the required chat
transcript. The zip must include `evaluation/usage_report.md`.

Before packaging, inspect the archive contents and verify that it contains code,
the usage report, required runtime files, and no API keys, private caches, or
unnecessary secrets.

### F-04 — High: strict read-back validation is structural, not a full financial re-simulation

The audit confirms row count, IDs, columns, supplied option references, and
spending-change syntax/eligibility checks. It does not by itself prove that
every serialized payment schedule preserves minimum balance at every date,
respects the deadline, or implements the intended opening-balance and horizon
semantics.

**Recommendation:** Before submission, run a context-aware post-serialization
simulation over the root `output.csv`, including:

- minimum balance after each payment and projected essential expense;
- payment-plan sum and chronological order;
- requested amount and desired-completion deadline;
- installment option identity and duration;
- partial-payment two-payment rules;
- flexible-only spending changes.

Treat any violation as a release blocker.

### F-05 — High: prediction quality remains materially uncertain

The latest 25-sample regression remains at 1/25 fully matching structured rows,
with exact safe-amount accuracy 1/25 and decision-field mismatches. The
250-request dry run has no ground truth and therefore cannot establish hidden
set accuracy.

This does not invalidate the complete artifact, but it means “250/250
processed” must not be presented as “250/250 correct.” Preserve the solved
sample metrics and the production structural audit separately.

### F-06 — Medium: policy provenance is present but release manifest is incomplete

The production metadata records the dataset, policy, extraction mode, and
timestamp, which is good. A final release manifest should additionally bind
the exact root output hash, usage-report hash, code archive hash, source Git
revision, and validation result.

### F-07 — Medium: cached usage attribution remains unresolved

The production usage file records repeated cache-hit records and zero current
calls. The repository decision log still marks cached-origin attribution as
requiring resolution. This is a submission-compliance issue, not a pipeline
execution failure.

## 6. What is complete versus what is missing

### Complete

- Full 250-request input traversal.
- Complete unique request coverage.
- Required serialized schema.
- Structural read-back validation.
- Supplied installment and spending-change checks.
- Cached extraction replay with no new calls.
- Reproducible policy and dataset metadata.
- No unsupported or failed production rows.

### Missing before final submission

1. Place the validated full-run output at root `output.csv`.
2. Independently re-validate the root output.
3. Generate nonempty `code/evaluation/usage_report.md` from the authoritative
   full-run usage and cache-origin records.
4. Run the final context-aware financial safety audit after serialization.
5. Create and inspect `code.zip`, including the usage report.
6. Prepare the required chat transcript and verify it contains no secrets.
7. Create a final manifest/checksum set tying output, code, usage, and policy
   to the same run.
8. Submit only after all package checks pass.

## 7. Final readiness verdict

| Readiness area | Verdict |
|---|---|
| Pipeline execution | **Ready** |
| Full input coverage | **Ready** |
| Output structure | **Ready in artifact; root copy required** |
| Deterministic cached replay | **Ready** |
| Financial correctness | **Unproven on hidden set; benchmark remains imperfect** |
| Safety validation | **Partially ready; independent serialized simulation recommended** |
| Usage reporting | **Not ready** |
| Submission packaging | **Not ready** |
| Overall Hackathon submission | **Almost ready, but do not submit yet** |

The project is achieving the core operational criteria of the Hackathon:
terminal execution, full request coverage, required schema, deterministic
replay, and validation boundaries. It has not yet achieved the final artifact
criteria because the required root output, usage report, package, transcript,
and final release manifest are incomplete.

## 8. Recommended final-run checklist

- [ ] Generate final root `output.csv` from the approved production run.
- [ ] Confirm 250 data rows, 250 unique IDs, exact header, and exact ID set.
- [ ] Run context-aware financial safety validation on the root file.
- [ ] Generate `code/evaluation/usage_report.md` with current and origin usage.
- [ ] Confirm report values correspond to the run producing root `output.csv`.
- [ ] Build `code.zip` and inspect its contents.
- [ ] Exclude API keys, `.env` files, private cache credentials, and secrets.
- [ ] Prepare `chat_transcript` from the append-only repository log.
- [ ] Record SHA-256 hashes for output, code archive, usage report, and manifest.
- [ ] Submit the final package through the HackerRank submission flow.

