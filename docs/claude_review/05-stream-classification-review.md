# Documentation Review 05: Stream Classification and Projection Phase

**Repository:** HackerRank Orchestrate - Buy or Wait?  
**Review date:** 2026-09-13  
**Scope:** New stream-classification/projection stage, forecast integration,
tests, diagnostics, and targeted evaluation artifacts. This review is advisory;
no code or existing documentation was changed.

## 1. Executive assessment

This is a sound architectural decomposition. Moving stream identity,
continuation, cadence, and amount estimation into [streams.py](../../code/buy_or_wait/streams.py)
allows [forecast.py](../../code/buy_or_wait/forecast.py) to focus on projecting
cash movements and simulating balances. That separation makes policy decisions
inspectable, testable, and independently replaceable.

The implementation also adds useful distinctions that the challenge needs:
transaction streams versus spending behavior, continuing versus terminated/
one-time/insufficient streams, independent salary sources, explicit terminal
payroll handling, conservative directional amount estimators, and contingency
reserves for category-level behavior.

The main limitation is unchanged overall challenge coverage. The targeted
request runs show that stream classification now reaches the planning boundary,
but planning strategies are still not implemented. The new stage therefore
improves the internal model and failure localization more than it improves
submission readiness.

**Current maturity:** strong stream-policy architecture and test foundation;
planning, evidence interpretation, and full-dataset coverage remain blocking.

## 2. Validation performed

The current full suite was run during this review:

```text
Ran 77 tests in 2.016s
OK
```

The repository task tracker reports the following milestone state:

- Stream identities and continuation states are implemented.
- Cadence inference and amount estimation are separated.
- Singleton history is classified as one-time.
- Uncertain income is excluded; unresolved recurring expenses block.
- Behavior-stream contingency reserves and stream diagnostics are present.
- `recurring-streams-v1-final` preserves one fully matching processed sample and
  zero comparable mismatches.

Targeted artifacts for requests 01, 13, 21, and 25 show no failed requests, but
each remains unsupported at the planning stage because no later/partial/
installment strategy is available. This is an important distinction: the new
stream stage is functioning, but the end-to-end request still does not produce
an output prediction.

## 3. What was completed well

### 3.1 Correct separation of concerns

The pipeline now has a clear sequence:

```text
normalize -> reconcile -> classify/project streams -> forecast -> plan
```

Forecasting consumes resolved stream projections instead of simultaneously
discovering recurrence and simulating balances. This reduces hidden coupling and
makes policy comparison feasible.

### 3.2 Stream identity is richer than the previous category key

Fixed transaction streams include normalized descriptions and currency, while
groceries, transport, and dining are treated as provisional behavior streams.
Repeated salary labels remain independent, reducing the risk of merging two
employers into one optimistic income stream.

### 3.3 Continuation states are explicit

`CONTINUING`, `TERMINATED`, `SUPERSEDED`, `ONE_TIME`, and
`INSUFFICIENT` make uncertainty visible. The asymmetric treatment—uncertain
income does not increase capacity while uncertain recurring expense blocks a
safe recommendation—is appropriate for a safety-first financial agent.

### 3.4 Amount policy is directional and inspectable

Using the maximum observed debit and minimum observed credit is conservative and
the policy is independent from cadence detection. This makes later policy
experiments possible without changing stream identity or forecast mechanics.

### 3.5 Behavior-contingency reserve addresses timing uncertainty

Category-level spending behavior is less exact than a billed transaction. The
additional maximum observed occurrence at the request boundary is a defensible
conservative reserve, provided it remains documented as a provisional policy and
is tested against double-counting.

### 3.6 Diagnostics preserve evidence

Stream source IDs, observed dates, intervals, cadence, continuation reason,
amount policy, and projections are retained in forecast diagnostics. This is
valuable for explaining why a request was blocked and for comparing policy
versions without changing sample labels.

## 4. Findings

### F-01 — Critical: stream classification does not yet produce end-to-end decisions

The new stage improves recurrence handling, but requests 01, 13, 21, and 25
still terminate at planning because later/partial/installment planning is not
implemented. The stage therefore does not yet increase final output coverage.

**Recommendation:** Treat stream classification as complete only at its own
stage boundary. Track end-to-end coverage separately, and implement baseline
capacity/earliest-date search and candidate planning next.

### F-02 — High: category-level behavior allowlist is an unvalidated policy

The allowlist `groceries`, `transport`, and `dining` is a reasonable starting
point, but it is a hardcoded semantic policy. Other essential or variable
categories may be omitted, while included categories may contain both recurring
and one-time purchases.

**Recommendation:** Add a policy table with category, essential/protected
classification, recurrence evidence threshold, estimator, and permitted
spending-change behavior. Validate the allowlist against the full dataset and
sample evidence without using sample answers. Keep category policy versioned.

### F-03 — High: description-based identity can merge unrelated transactions

Normalized description labels are useful for fixed transactions, but identical
or near-identical descriptions can represent different merchants, contracts,
accounts, or lifecycle sources. The current model has no explicit source/account
identifier beyond the available event fields.

**Recommendation:** Use the strongest available provenance hierarchy—user,
event type/category, normalized description, currency, source/lifecycle lineage,
and temporal consistency. If two candidate streams cannot be distinguished,
classify them as ambiguous rather than merge them into optimistic recurrence.

### F-04 — High: missing-occurrence logic may be too eager for irregular income

The stage marks a stream insufficient when an expected occurrence is missing.
That is safe for a strict fixed bill, but it may reject valid irregular income,
seasonal expenses, payroll holidays, or one-off schedule changes.

**Recommendation:** Make missing-occurrence behavior stream-class dependent.
Require stronger continuity evidence for income, but distinguish a genuinely
terminated stream, a temporarily delayed occurrence, and an irregular stream.
Do not treat a missing occurrence as zero cash or silently continue it.

### F-05 — High: projected amount and FX timing need a single explicit contract

Stream amount estimation is performed in the event currency, while forecast
conversion uses the request/start date for behavior-contingency reserves and
settlement dates for projected stream entries. This may be correct under the
challenge rules, but the contract should explicitly state the rate date for
each projection type.

**Recommendation:** Document:

- historical event conversion date;
- inferred occurrence conversion date;
- pending-debit reservation conversion date;
- behavior-contingency conversion date;
- missing-rate failure behavior.

Add an end-to-end mixed-currency stream fixture where changing the supplied
rate changes capacity.

### F-06 — Medium: cadence tolerance can create multiple plausible identities

The stage permits one day of fixed-interval drift and two days of monthly drift.
The current implementation selects a cadence only when exactly one fixed
candidate matches, which is good, but the policy needs boundary tests for
overlapping candidates and month-end dates.

**Recommendation:** Add fixtures for 5/7/10/14/21/28-day candidate overlap,
month-end rollover, February, leap years, and drift at tolerance minus/equal/
plus one. Record ambiguity as insufficient rather than selecting a convenient
cadence.

### F-07 — Medium: stream continuation and lifecycle resolution need a formal contract

Stream classification consumes reconciled events, but the documentation should
state which reconciliation treatments are eligible for history, which are
eligible for projection, and how terminal markers, successor events, refunds,
and reservations affect source membership.

**Recommendation:** Add a stream-input/output schema and a matrix:

```text
raw/resolved treatment -> history eligibility -> identity -> continuation
-> cadence -> amount policy -> projected dates
```

Require source lineage for every projection and an explicit reason for every
excluded event.

### F-08 — Medium: behavior contingency may double-count explicit future events

The forecast intentionally reserves a behavior contingency at the request
boundary and separately processes explicit future events. Although explicit
occurrences suppress matching projections, the contingency is category-level
and may coexist with a real request-date expense or pending debit.

**Recommendation:** Add adversarial tests for:

- pending debit plus behavior contingency;
- explicit request-date behavior event;
- explicit future event matching an inferred occurrence;
- multiple behavior streams in one category;
- no historical behavior but a single future event.

Document whether the contingency is a reserve floor, an additional event, or a
capacity reduction so downstream planning cannot count it twice.

### F-09 — Medium: stream diagnostics are not yet part of evaluator artifacts

The application writes diagnostics under output-relative directories, while the
evaluation runner primarily retains predictions, metrics, request results, and
usage. The review should verify that stream diagnostics are preserved and
associated with the evaluator run ID rather than being overwritten or detached.

**Recommendation:** Add diagnostic paths or hashes to each request result and
include stream-policy version and diagnostic manifest entries in the evaluation
artifact directory.

### F-10 — Low: compatibility wrapper risks duplicate policy paths

`forecast.infer_occurrences()` remains as a compatibility wrapper while the
application uses `resolve_streams()`. Duplicate entry points can drift if one is
updated without the other.

**Recommendation:** Either remove the wrapper after callers migrate, or make it
delegate exclusively to the stream classifier and add a test proving identical
policy results for equivalent inputs.

## 5. Phase verdict

| Dimension | Verdict |
|---|---|
| Architecture decomposition | **Strong** |
| Stream identity model | **Promising, provisional** |
| Safety posture | **Strong** — uncertainty does not create spendable capacity. |
| Test coverage | **Strong for synthetic stream policies** — 77 tests pass. |
| Dataset coverage | **Insufficient** — targeted cases reach planning but do not produce decisions. |
| Forecast separation | **Improved materially** |
| Submission readiness | **Not ready** — candidate planning and evidence remain. |

## 6. Prioritized next steps

### P0 — make projections useful to planning

- Implement baseline safe capacity and earliest safe full-payment date.
- Add later/wait candidate generation.
- Add exact installment-option simulation and validation.
- Add prescribed partial-payment construction.
- Re-simulate every serialized candidate independently.

### P1 — validate stream policy against financial semantics

- Formalize category behavior policy and essential/protected interactions.
- Add stream-input/output schemas and treatment lineage.
- Add missing-occurrence, month-end, overlapping-cadence, and FX-date fixtures.
- Validate contingency reserves against explicit/pending event double counting.
- Remove or constrain duplicate forecast compatibility paths.

### P2 — extend evidence and release integration

- Add relevance-scoped message/image extraction after the deterministic boundary.
- Preserve stream diagnostics in evaluator artifacts and final traces.
- Add 250-request release validation independent of sample answers.
- Generate the required final usage report from the authoritative full run.

## 7. Recommended next-milestone acceptance criteria

- [ ] All 77 tests remain green.
- [ ] At least one stream-projected case reaches a valid non-full-payment plan.
- [ ] A plan is independently validated after CSV serialization.
- [ ] Behavior-contingency reserve has explicit no-double-counting regressions.
- [ ] Mixed-currency projected stream has an end-to-end FX regression.
- [ ] Missing-occurrence behavior is documented separately for income,
  fixed expenses, and variable behavior streams.
- [ ] Stream diagnostics are linked to evaluator request artifacts.
- [ ] Coverage increases beyond 1/25 without weakening fail-closed safety.
