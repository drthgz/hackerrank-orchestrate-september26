# Active tasks

## Current phase

Final targeted deterministic pass complete; production dry run is awaiting review.

## In progress

- [x] Inventory all 19 solved-sample evidence requirements without using expected outputs.
- [x] Add deterministic-first message parsing and narrow message/image fact extraction.
- [x] Add versioned cache, provenance diagnostics, controlled failures, and measured usage.
- [x] Run representative live extraction and populate the solved-sample cache.
- [x] Review final cached benchmark artifact and extraction/downstream failure split.
- [x] Aggregate same-day spending behavior observations and resolve request_17 without a special case.
- [x] Build per-request safe-capacity traces and cluster the 90 comparable mismatches.
- [x] Remove the unsupported extra behavior occurrence; retain cadence-derived spending.
- [x] Apply protected-maximum versus non-protected-mean amount policy.
- [x] Honor confirmed dated salary facts independently of historical recurrence.
- [x] Record `forecast-capacity-v3-final`: 25 processed, 0 unsupported/failed, 1 fully matching row, 88 comparable mismatches, zero model calls.
- [x] Trace request_03, request_20, and request_21 overpredictions and classify their cash timelines.
- [x] Require explicit flexible event metadata before using a non-conservative mean expense estimate.
- [x] Add the 25-row before/after diagnostic table and record `safety-pass-v1-fixed-streams`.
- [x] Stop further tuning where residual differences lack a repository-supported general rule.

## Next

- [ ] Review residual forecast-policy uncertainty before the 250-request dry run.
- [ ] Preserve cached extraction and run production diagnostics without sample tuning.

## Completed

- [x] Inspect repository requirements, input schemas, examples, representative evidence, and empty starter files.
- [x] Verify identifiers/evidence links, missing-amount image coverage, and supplied installment arithmetic.
- [x] Agree controlled pipeline and deterministic/AI boundary.
- [x] Establish design, phased plan, task tracker, and material decision log.
- [x] Record unit, benchmark, regression, extraction, and release-validation loops.
- [x] Identify request_01 and request_09 as candidates using input/context complexity only: no messages/images or FX; recurrence still required.
- [x] Add external sample-input projection and strict application input schema; test answer mutation/rejection.
- [x] Add structured CSV loading, relationship checks, typed facts with Decimal/date/provenance, serialization, and independent structural validation.
- [x] Add focused synthetic contract tests and selected-input normalization checks.
- [x] Implement isolated versioned provisional forecast, full-payment sufficient-case decision, application entry point, and staged output validation.
- [x] Run request_09 end to end and compare outside application logic: seven structured fields match; explanation differs intentionally.
- [x] Keep request_01 as an explicit unsupported-case test; no unjustified prediction.
- [x] Pass 29 focused tests, including 15 new policy/end-to-end tests and pending-credit suppression regression.
- [x] Document the runnable command in README; no model calls, evaluator, final output, commits, or pushes.

- [x] Build code/evaluation harness: selection, isolated inputs/answers, semantic comparison, per-request outcomes, immutable run artifacts, metadata, and zero-usage foundation.
- [x] Add 17 evaluator tests; all 46 tests pass, including the existing 29.
- [x] Complete smoke-v1: 2 selected, 1 processed/matching, 1 unsupported.
- [x] Record baseline-v1: 25 selected, 2 processed, 21 unsupported, 2 failed; 1 fully matching structured row.
- [x] Record 5 comparable financial mismatches, 138 missing fields, and 2 prose diagnostics; no benchmark failures fixed. See [evaluator baseline notes](../code/evaluation/README.md).

- [x] Preserve request_05 pre-change chronological trace; identify invented post-terminal salary as the false-positive cause.
- [x] Add narrow terminal-payroll parsing, valid non_cash normalization, explicit lifecycle reconciliation/provenance and reservation-release handling.
- [x] Add exact settlement-date FX conversion after scope assessment; leave household income identity and transport cadence unresolved.
- [x] Pass 65 tests (19 new regressions); run all requested targeted evaluations and final 25-sample run without further mismatch patches.
- [x] Record v2: 1 processed, 24 unsupported, 0 failed, 1 matching row; comparable financial mismatches 5 -> 0 because the false-positive output is withheld.
- [x] Add explicit transaction/behavior stream identities, independent salary sources, and lifecycle-safe source membership.
- [x] Add continuation states, stale/missing-occurrence detection, deterministic cadence inference, and separate amount estimation.
- [x] Classify singleton history as one-time; exclude uncertain income and block unresolved recurring expenses.
- [x] Add behavior-stream contingency reserves and inspectable stream diagnostics; pass 77 tests.
- [x] Record `recurring-streams-v1-final`: 1 processed, 24 unsupported, 0 failed, 1 matching, zero comparable mismatches.
- [x] Add simulation-based immediate capacity and earliest safe full-payment date search.
- [x] Add full, wait, partial, supplied-installment, flexible-change, and not-recommended candidates.
- [x] Add independent candidate eligibility, simulation, ranking, rejection diagnostics, and planning artifacts.
- [x] Add 13 planning tests; all 90 tests pass.
- [x] Record `planning-v1-final`: 6 processed, 19 unsupported, 0 failed, 1 fully matching row.
- [x] Add typed extracted facts, strict schema grounding, user/event ownership checks, and source/model/version provenance.
- [x] Add `live`, `cached`, and `deterministic-only` evaluator modes with real usage and cache accounting.
- [x] Add message/image fixtures and regression coverage; live model calls remain outside unit tests.
- [x] Record `selective-extraction-v2-final-cached-verified`: 24 processed, 1 forecast-unsupported, 0 failed, 1 fully matching row; zero model calls and 10 cache hits.

## Blocked / needs decision

- [x] Obtain implementation authorization for the vertical slice only.
- [x] User authorized explicit provisional recurrence and conservative same-day ordering.
- [ ] Resolve opening-balance timing, pending-hold treatment, horizon boundaries, and same-day ordering before the full financial engine.
- [ ] Validate provisional behavior categories, one-occurrence contingency, cadence tolerance, and min/max amount estimators against broader evidence.
- [ ] Confirm whether `max_installment_months` limits payment count or elapsed calendar months.
- [ ] Resolve installment duration, deadline/status edge cases, and recurring spending-change targeting before complete planning.
- [ ] Fix rounding/tie-break conventions and cached-usage accounting before release; see [decisions.md](decisions.md).

## Maintenance

Update when meaningful tasks start or finish. Keep only immediate actionable work here; future milestones live in [plan.md](plan.md). The user creates commits; do not commit or push. Leave `.env`, `.gitignore`, and dataset files unchanged unless separately instructed. Append the required conversation log under `AGENTS.md` rules.
