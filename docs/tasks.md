# Active tasks

## Current phase

Phase 2 — minimal vertical slice authorized and in progress. Evaluator remains out of scope.

## In progress

- Complete the minimal processing and runnable path after the pending forecasting-scope decision.

## Next

- [ ] Resolve the narrow forecast versus diagnostic-only scope question (asked during implementation).
- [ ] Implement the agreed deterministic processing, entry point, and selected-path end-to-end test.
- [ ] Run selected predictions, compare outside application logic, and document the runnable command.

## Completed

- [x] Inspect repository requirements, input schemas, examples, representative evidence, and empty starter files.
- [x] Verify identifiers/evidence links, missing-amount image coverage, and supplied installment arithmetic.
- [x] Agree controlled pipeline and deterministic/AI boundary.
- [x] Establish design, phased plan, task tracker, and material decision log.
- [x] Record unit, benchmark, regression, extraction, and release-validation loops.
- [x] Identify request_01 and request_09 as candidates using input/context complexity only: no messages/images or FX; recurrence still required.
- [x] Add external sample-input projection and strict application input schema; test answer mutation/rejection.
- [x] Add structured CSV loading, relationship checks, typed facts with Decimal/date/provenance, serialization, and independent structural validation.
- [x] Add focused synthetic contract tests and selected-input normalization checks (no financial predictions yet).

## Blocked / needs decision

- [x] Obtain implementation authorization for the vertical slice only.
- [ ] User clarification pending: authorize a narrow explicit provisional forecast, or stop at diagnostic output until forecast policy is agreed. Current-balance-only output would violate the 90-day requirement.
- [ ] Resolve opening-balance timing, pending-hold treatment, horizon boundaries, and same-day ordering before the full financial engine.
- [ ] Specify recurrence/conservative-spending policies and amendment scope before forecasting implementation.
- [ ] Resolve installment duration, deadline/status edge cases, and recurring spending-change targeting before complete planning.
- [ ] Fix rounding/tie-break conventions and cached-usage accounting before release; see [decisions.md](decisions.md).

## Maintenance

Update when meaningful tasks start or finish. Keep only immediate actionable work here; future milestones live in [plan.md](plan.md). The user creates commits; do not commit or push. Leave `.env`, `.gitignore`, and dataset files unchanged unless separately instructed. Append the required conversation log under `AGENTS.md` rules.
