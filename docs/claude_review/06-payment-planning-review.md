# Documentation Review 06: Deterministic Payment Planning Phase

**Repository:** HackerRank Orchestrate - Buy or Wait?  
**Review date:** 2026-09-13  
**Scope:** Deterministic payment planning engine, candidate validation/ranking,
serialized-output behavior, tests, and `planning-v1-final` evaluation artifacts.
This review is advisory; no code or existing documentation was changed.

## 1. Executive assessment

This phase is a substantial milestone and supports the project’s approximate
70% completion assessment. The new planner converts the resolved forecast into
finite, simulated candidates for full payment, waiting, partial payment,
supplied installments, flexible spending changes, and not-recommended outcomes.
It also introduces cent-denominated binary-search capacity, earliest-safe-date
search, candidate rejection diagnostics, and deterministic ranking.

The phase changes the nature of the remaining work. Previously, many sample
requests stopped because architecture was missing. Now five additional
requests reach full evaluation, and the remaining failures are primarily
forecast-policy or evidence limitations. That is exactly the right progression:
planning is now a real subsystem rather than a placeholder.

The benchmark still exposes important accuracy gaps. `planning-v1-final`
processes 6/25 samples, with 1/25 fully matching all structured fields. The
planner has also surfaced a material capacity discrepancy in `request_01` and
an amount mismatch in `request_05`; these should be analyzed as forecast/capacity
policy issues, not patched with request-specific rules.

**Current maturity:** credible deterministic planning engine; not yet
submission-ready because forecast policy, evidence extraction, and full
evaluation coverage remain incomplete.

## 2. Validation and results reviewed

The repository task tracker reports **90 tests passing** after 13 planning
tests were added. The final planning artifact reports:

| Measure | Result |
|---|---:|
| Solved samples selected | 25 |
| Processed | 6 |
| Unsupported | 19 |
| Failed | 0 |
| Fully matching structured rows | 1 |
| Comparable structured mismatches | 18 |
| Missing prediction fields | 114 |
| Model calls/tokens/cost | 0/0/0 |

The planner therefore increased coverage from 1/25 in the stream phase to 6/25
without introducing failed requests. That is meaningful progress even though
end-to-end accuracy remains low.

## 3. What was completed well

### 3.1 Candidate generation covers the required strategy families

The planner now constructs candidates for:

- immediate full payment;
- waiting until the earliest safe full-payment date;
- prescribed two-payment partial payment;
- supplied installment options;
- full payment after eligible spending changes;
- explicit not-recommended fallback.

This directly maps to the challenge output contract.

### 3.2 Simulation is used as the hard safety boundary

Every candidate is simulated against the forecast timeline, and candidates
below the minimum balance are rejected. This keeps planning deterministic and
prevents a ranking function from selecting an unsafe plan.

### 3.3 Capacity and recommendation are separated

`safe_capacity()` and `earliest_safe_full_date()` are calculated before
candidate ranking. This preserves the challenge distinction between baseline
`amount_safe_to_pay`/earliest date and the user’s preferred payment method or
spending changes.

### 3.4 Spending changes are constrained

Candidate changes are sourced from continuing debit streams, exclude protected
categories, honor stop/reduce permissions, use minimum allowed amounts, and
enumerate combinations up to three actions. This is a good fail-closed
foundation for flexible-spending recommendations.

### 3.5 Candidate diagnostics are inspectable

Each candidate records eligibility, rejection reason, minimum projected balance,
completion date, and rank. This is valuable for explaining why a supplied
installment or spending-change strategy lost or failed.

### 3.6 The phase preserves deterministic and reproducible behavior

No model calls were introduced, the existing test suite remains green, and the
planner operates on resolved forecasts rather than sample answers.

## 4. Findings

### F-01 — Critical: installment-duration semantics remain provisional

The planner currently compares `option.number_of_payments` to
`max_installment_months`. The task tracker and decisions log still identify
whether this field means payment count or elapsed calendar months as unresolved.

**Impact:** A valid supplied option can be incorrectly rejected or accepted,
changing method, status, and plan outputs.

**Recommendation:** Resolve this against the challenge semantics and supplied
option intervals. Add boundary fixtures for one payment per month, multiple
payments within one month, and elapsed duration at the exact limit. Record the
policy version in planning metadata.

### F-02 — High: request_01 exposes a material capacity/forecast mismatch

The planner produces `amount_safe_to_pay=0` and `not_affordable`, while the
sample expects an immediate full payment of 25,256. The plan fields are
structurally valid, but the forecast is too conservative or otherwise
misclassified for this case.

**Recommendation:** Reconstruct request_01’s chronological balance trace,
including recurring groceries, lifecycle replacements, opening balance, and
same-day ordering. Determine whether the discrepancy is caused by behavior
contingency, recurrence identity, duplicated reserve, or an opening-balance
assumption. Add a generalized regression fixture only after identifying the
financial rule; do not tune the request ID.

### F-03 — High: amount-safe capacity and not-recommended output semantics need explicit review

For `request_05`, the planner correctly matches status, method, plan, earliest
date, and spending changes, but emits `amount_safe_to_pay=0` while the sample
expects 737. This may be a legitimate conservative-policy difference, but the
output contract defines amount safe as the largest safe amount before optional
changes.

**Recommendation:** Verify whether capacity search should permit a positive
partial amount while the full request remains impossible. Add tests for:

- positive safe amount but no complete plan;
- zero safe amount and no complete plan;
- partial payment permitted but deadline missed;
- safe capacity after optional spending changes versus baseline capacity.

### F-04 — High: planner validation is not yet fully independent of planner logic

The planner evaluates candidates before serialization, while the current output
validator checks structural consistency and basic method shapes. Installment
matching, flexible-event eligibility, minimum-balance safety, and option
duration should also be checked by a separate post-serialization validator
against the resolved context.

**Recommendation:** Add a context-aware release validator that re-parses the
CSV, reconstructs each payment/change, matches supplied options exactly,
re-simulates the plan, and verifies baseline capacity fields independently.

### F-05 — High: ranking implementation should be documented against the published order

The rank key prioritizes no changes, change count, total paid, start date,
payment count, option ID, and method order. The challenge ranking first
prioritizes completion by deadline, then no changes, total cost, earlier start,
fewer payments, and lowest option ID.

The current candidate set already filters late candidates, which may be
equivalent for some cases, but the equivalence is not documented. The
additional `method_order` tie-break is an implementation policy not present in
the challenge contract.

**Recommendation:** Document the exact lexicographic rank tuple, prove that
deadline filtering is equivalent to the first ranking criterion, and define
method tie-breaking only when all published keys are equal. Add tie fixtures.

### F-06 — Medium: full-payment options should validate financing semantics

The planner accepts a full option when method, payment count, date, total, and
requested amount match, but the candidate does not explicitly require
zero financing fee in `_base_candidates`. A full-payment option with an
unexpected fee could be treated as a valid full candidate if its total equals
the request.

**Recommendation:** Make full-payment eligibility explicit: exact supplied
schedule, total payable, fee policy, user preference, and request date. Add
malformed/fee-bearing option fixtures.

### F-07 — Medium: spending-change targeting is still a provisional projection

The planner chooses the latest source event from a stream as the action target
and applies changes to entries whose `source_ids` contain that event. This is
reasonable for a first policy, but recurring stream actions need explicit
effective scope and must not alter already-settled history or unrelated
occurrences.

**Recommendation:** Document change effective date and scope. Add tests for
multiple source events, pending reservations, behavior contingency entries,
foreign-currency reductions, protected categories, and stop/reduce exclusivity.

### F-08 — Medium: candidate evaluation does not expose all eligibility reasons

Some constraints are enforced by candidate construction rather than recorded as
rejection diagnostics. This makes it difficult to distinguish “not generated,”
“generated but ineligible,” and “not safe.”

**Recommendation:** Emit candidate-generation counters and explicit rejection
reasons for user method preference, partial-payment permission, deadline,
installment duration, option mismatch, change eligibility, and simulation
failure.

### F-09 — Low: explanation output is too generic for final quality

Planner explanations state the selected method and projected minimum balance,
but do not identify the relevant income/expense facts, deadline, option, or
spending changes. This is acceptable for a development slice but below the
challenge’s usefulness expectation.

**Recommendation:** Generate deterministic explanations from verified candidate
facts: request amount, safe amount, selected option/payment dates, minimum
reserve, key blocking reason, and any spending actions. Keep prose separate
from structured scoring.

## 5. Phase verdict

| Dimension | Verdict |
|---|---|
| Strategy coverage | **Strong improvement** |
| Safety simulation | **Good foundation** |
| Candidate diagnostics | **Good and inspectable** |
| Test discipline | **Strong** — 90 tests reported passing |
| Benchmark coverage | **Improved** — 6/25 processed |
| Forecast/capacity correctness | **Needs investigation** — request_01 and request_05 mismatches |
| Submission readiness | **Not ready** — evidence, full dataset, and final validation remain |

## 6. Prioritized next steps

### P0 — resolve forecast/capacity mismatches

- Trace request_01 from resolved events through streams, forecast, capacity, and
  candidate rejection.
- Define positive-safe-capacity semantics for request_05.
- Add generalized regression fixtures for both findings.
- Keep request-specific labels out of the implementation.

### P1 — harden planner contract

- Resolve installment-month semantics.
- Add independent context-aware post-serialization validation.
- Verify published ranking and tie-break behavior.
- Complete spending-change effective-scope rules.
- Expand candidate diagnostics and deterministic explanations.

### P2 — increase end-to-end coverage

- Add narrow evidence extraction for message/image-dependent requests.
- Run the full 25-sample benchmark after each coherent policy change.
- Add a separate 250-request release runner and final output validation.
- Generate the required final usage report from the authoritative run.

## 7. Recommended next-milestone acceptance criteria

- [ ] All 90 tests remain green.
- [ ] Request_01 capacity mismatch has a documented generalized cause and test.
- [ ] Request_05 positive-capacity semantics are explicitly tested.
- [ ] At least one installment and one partial/wait plan pass independent
  serialized-output safety validation.
- [ ] Installment duration semantics are resolved and versioned.
- [ ] Ranking tie cases match the published challenge order.
- [ ] Spending-change effective scope and target selection are regression-tested.
- [ ] Full benchmark reports coverage, end-to-end accuracy, conditional accuracy,
  comparable mismatches, and safety-validation outcomes separately.
