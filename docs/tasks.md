# Active tasks

## Current phase

Targeted deterministic correctness/reconciliation milestone complete; baseline-v1 and final deterministic-core-v2 evaluation preserved. Awaiting user review; no AI extraction.

## In progress

- None; targeted milestone complete.

## Next

- [ ] Review v1 trace and v2 comparison before further implementation.
- [ ] Define evidence-based recurring-stream identity/termination and one-time-event eligibility, including household income and investment contributions.
- [ ] Investigate conservative expense-policy limitations and general safe-capacity behavior; do not tune to sample IDs.

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

## Blocked / needs decision

- [x] Obtain implementation authorization for the vertical slice only.
- [x] User authorized explicit provisional recurrence and conservative same-day ordering.
- [ ] Resolve opening-balance timing, pending-hold treatment, horizon boundaries, and same-day ordering before the full financial engine.
- [ ] Specify recurrence/conservative-spending policies and amendment scope before forecasting implementation.
- [ ] Resolve installment duration, deadline/status edge cases, and recurring spending-change targeting before complete planning.
- [ ] Fix rounding/tie-break conventions and cached-usage accounting before release; see [decisions.md](decisions.md).

## Maintenance

Update when meaningful tasks start or finish. Keep only immediate actionable work here; future milestones live in [plan.md](plan.md). The user creates commits; do not commit or push. Leave `.env`, `.gitignore`, and dataset files unchanged unless separately instructed. Append the required conversation log under `AGENTS.md` rules.
