# Material decisions

Accepted entries identify either confirmed repository rules or agreed engineering choices. Revisit entries are unresolved proposals, not implementation defaults. Sources: [problem statement](../problem_statement.md), [README](../README.md), [AGENTS.md](../AGENTS.md).

## Decision: Controlled deterministic pipeline

Status: Accepted

Context: The challenge combines structured financial records and unstructured evidence; behavior should be deterministic where possible.

Decision: AI handles selective perception/interpretation. Deterministic software owns financial reasoning, enforcement, ranking, and validation. Use deterministic parsers where coverage is clear; otherwise one narrow extraction contract. No autonomous/multi-agent architecture.

Reason: Agreed engineering choice for correctness, testing, cost, latency, and auditability.

Alternatives considered: LLM-generated decisions; universal model fallback; agent frameworks.

Consequences: Financial policies must be explicit and tested. AI may propose semantic facts, never invent policy or override constraints.

## Decision: Decimal financial arithmetic

Status: Accepted

Context: Monetary bounds, FX, and schedule totals require stable comparisons.

Decision: Parse monetary values directly into Decimal; use explicit rounding rules once settled. Do not use binary floating point for financial calculations.

Reason: Agreed engineering choice avoiding representation errors at safety boundaries.

Alternatives considered: Binary floats with tolerances; scaled integers before currency precision is established.

Consequences: Exact comparisons are possible; quantization stage and rounding mode remain to be specified.

## Decision: Versioned evidence cache and provenance

Status: Accepted

Context: Fresh model calls can vary, while deterministic changes should not require repeated extraction.

Decision: Cache extracted facts by content, relevant context, model, prompt, and schema version. Retain source references and separate assertions from resolved facts.

Reason: Agreed engineering choice for reproducibility, cost, and failure attribution.

Alternatives considered: Re-extract every run; cache only by filename; discard source evidence.

Consequences: Financial configurations can share frozen facts. Extraction changes invalidate affected entries. Track actual run usage and originating cached usage separately.

## Decision: Unresolved evidence is not a financial conclusion

Status: Accepted

Context: Blank amounts cannot mean zero; the required output has no unknown status.

Decision: Preserve explicit unresolved states, use bounded extraction recovery, and block final artifact release for material unresolved data. Do not disguise a processing failure as `not_affordable`.

Reason: Repository prohibition on invented facts plus agreed safety boundary.

Alternatives considered: Zero defaults; invented estimates; unrestricted LLM fallback; automatic rejection output for errors.

Consequences: Development diagnostics may be incomplete, but final release requires material issues resolved.

## Decision: Isolated benchmark answers and layered testing

Status: Accepted

Context: Twenty-five solved samples are available; hidden scoring weights are not supplied.

Decision: Keep expected outputs exclusively in the evaluator. Use deterministic unit tests, sample field metrics/mismatches, focused adversarial/regression tests, reviewed extraction tests, and independent final validation. Compare financial strategies on frozen facts.

Reason: Repository forbids hardcoded labels; agreed approach enables honest evaluation and causal debugging.

Alternatives considered: Passing sample answers to the pipeline; exact explanation-text matching as the main score; end-to-end tests alone.

Consequences: No invented official aggregate score. Reviewed intermediate facts are needed to attribute extraction failures reliably.

## Decision: Baseline capacity and candidate ranking

Status: Accepted

Context: Repository capacity fields differ from selected-plan behavior.

Decision: Compute safe amount/earliest full date without optional changes; earliest date ignores method preferences. Apply payment eligibility and full-plan safety, then published ranking: deadline, no changes, lowest total cost, earlier start, fewer payments, lowest option ID. Partial payment uses exactly the prescribed two payments; installments match a supplied option.

Reason: Confirmed repository requirements, illustrated by samples selecting installments despite full capacity or full payment after spending changes.

Alternatives considered: Model ranking; equating earliest full date to final installment; changing baseline fields after reductions.

Consequences: Capacity and recommendation are separate outputs. Deadline/status edge cases and exact ID ordering remain open below.

## Decision: Settlement-date FX and cash-state handling

Status: Accepted

Context: Foreign-currency events and linked lifecycle records can misstate available cash.

Decision: Use exact supplied settlement-date/directional FX rates. Reserve pending debits; exclude pending credits and unrealized values. Count supported salary on settlement date. Resolve lifecycle links semantically, not by deleting every linked event. Apply published conflict precedence to normalized facts.

Reason: Confirmed repository requirements.

Alternatives considered: Live rates; event-date conversion; treating every link as a duplicate; counting expected windfalls.

Consequences: Missing required conversion/evidence is explicit. Opening-balance interaction and future recurrence still need policy.

## Decision: Opening balance, horizon, and same-day ordering

Status: Revisit

Context: The profile supplies current available balance and the rules require 90-day safety, but precise snapshot/hold and within-day conventions are not fully specified.

Decision: Proposed starting point: use the supplied balance as the request snapshot and historical events for inference, not replay. Verify pending holds, same-day settled records, exact day-90 inclusion, fixed request-relative horizon, and within-day event/payment ordering before implementation.

Reason: Double counting or optimistic ordering can invalidate all capacity results.

Alternatives considered: Reconstructing balance by replay; rolling 90 days from each candidate date; daily netting; debits-first ordering.

Consequences: Validate interpretations against supporting records and samples; explicitly document any convention the repository cannot resolve. No model chooses it.

## Decision: Recurrence, variable spending, and amendments

Status: Revisit

Context: Recurrence must be supported and variable essentials conservative; no complete estimator is prescribed.

Decision: Specify historical window, cadence evidence, amount estimator, month-end behavior, explicit/inferred occurrence deduplication, and temporary versus recurring amendment scope before forecasting implementation.

Reason: Determinism alone does not establish a correct forecast.

Alternatives considered: Recent maximum/quantile/other documented estimators; recurring salary supported by history versus only explicit next salary; blanket extrapolation (not acceptable).

Consequences: Compare defensible configurations on frozen facts; add independent tests and avoid request-ID rules or invented expenses/income.

## Decision: Planning edge conventions

Status: Revisit

Context: Day-based installment intervals are explicit, but several peripheral conventions remain unclear.

Decision: Resolve mapping to `max_installment_months`, capacity after deadline versus output status, recurring-change target event/effective date, rounding/quantization, and numeric versus lexical option-ID tie-breaks. Supplied day intervals and amounts remain authoritative; never silently rewrite schedules.

Reason: Small boundary choices can change eligibility and hidden-test outcomes.

Alternatives considered: Payment count versus elapsed-month duration; calendar-month substitution (inconsistent with supplied day intervals); different stable ID orderings.

Consequences: Add boundary fixtures. Current options sum exactly, but malformed future inputs still need validation rather than automatic repair.

## Decision: Final-run cached usage attribution

Status: Revisit

Context: Required usage report covers the final run; reused evidence may have incurred model cost in an earlier extraction run.

Decision: Preserve both actual final-run usage and cached-origin usage; settle report attribution before release and label each clearly.

Reason: A zero-call replay must not imply evidence extraction had no cost.

Alternatives considered: Report only current calls; attribute all cache creation cost without distinguishing reuse.

Consequences: Usage ledger must retain origin run, provider/model, calls, input/output tokens, costs, and per-request attribution. Do not invent an organizer policy.
