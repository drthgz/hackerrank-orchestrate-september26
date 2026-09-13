# Active tasks

## Current phase

Phase 1 — architecture/documentation foundation complete. Next: phase 2, minimal vertical slice. Application implementation is not yet authorized.

## In progress

- None. Documentation-only request completed.

## Next

- [ ] Select 1–2 simple sample requests without essential unstructured dependencies; keep expected answers outside pipeline context.
- [ ] Define the narrow vertical-slice input/output contracts and its explicit limitations.
- [ ] After authorization, implement CSV loading and request context construction for the selected inputs.
- [ ] Normalize structured facts and add minimal deterministic processing.
- [ ] Serialize a correctly shaped provisional prediction and validate structure.

## Completed

- [x] Inspect repository requirements, input schemas, examples, representative evidence, and empty starter files.
- [x] Verify identifiers/evidence links, missing-amount image coverage, and supplied installment arithmetic.
- [x] Agree controlled pipeline and deterministic/AI boundary.
- [x] Establish design, phased plan, task tracker, and material decision log.
- [x] Record unit, benchmark, regression, extraction, and release-validation loops.

## Blocked / needs decision

- [ ] Obtain implementation authorization before starting the vertical slice.
- [ ] Resolve opening-balance timing, pending-hold treatment, horizon boundaries, and same-day ordering before the full financial engine.
- [ ] Specify recurrence/conservative-spending policies and amendment scope before forecasting implementation.
- [ ] Resolve installment duration, deadline/status edge cases, and recurring spending-change targeting before complete planning.
- [ ] Fix rounding/tie-break conventions and cached-usage accounting before release; see [decisions.md](decisions.md).

## Maintenance

Update when meaningful tasks start or finish. Keep only immediate actionable work here; future milestones live in [plan.md](plan.md). The user creates commits; do not commit or push. Leave `.env`, `.gitignore`, and dataset files unchanged unless separately instructed. Append the required conversation log under `AGENTS.md` rules.
