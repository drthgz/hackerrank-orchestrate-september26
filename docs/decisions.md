# Material decisions

Accepted entries identify either confirmed repository rules or agreed engineering choices. Revisit entries are unresolved proposals, not implementation defaults. Sources: [problem statement](../problem_statement.md), [README](../README.md), [AGENTS.md](../AGENTS.md).

## Decision: Forecast-capacity v3 amount and occurrence policy

Status: Accepted

Context: The cached solved-sample trace showed every v2 safe-amount error was downward. Category behavior used a maximum amount for every occurrence and inserted an additional maximum occurrence on the request date. Same-day purchases also caused an unsupported duplicate-date cadence failure. Confirmed dated salary evidence was ignored unless historical recurrence independently resolved.

Decision: Aggregate genuine same-day category purchases into one daily cadence observation while retaining all source IDs. Project only cadence-derived occurrences; remove the extra request-date contingency. Keep conservative maximum amounts for protected expense streams. Continue non-protected flexible/other recurring spending at its observed mean. Treat high-confidence dated salary evidence as a direct future cash fact: one occurrence remains one occurrence, while explicitly ongoing salary repeats monthly. A targetless explicit payroll-date amendment may attach only to the unique latest supplied payroll event when the message says it replaces that date.

Reason: These rules preserve protected obligations and flexible spending while removing an invented occurrence, resolving valid daily aggregation, and honoring direct confirmed future evidence. Across all solved samples they reduce safe-amount MAE from 997,908.43 to 107,276.24 without validation changes or benchmark-specific conditions.

Alternatives considered: Omit flexible spending; average protected expenses; retain an undated contingency; infer salary from singleton history; tune per-request amounts.

Consequences: All 25 solved samples now run with frozen cached evidence. Three safe amounts exceed solved values and require review before further relaxation. The remaining 21 underestimated rows point to event eligibility, continuation, cadence, and horizon policy. Exact safe-amount matches remain 1/25, so this is an improved deterministic baseline rather than final policy.

## Decision: Narrow versioned evidence extraction

Status: Accepted

Context: Nineteen solved samples contain messages or images that block an otherwise deterministic pipeline.

Decision: Apply explicit deterministic patterns first, then one strict Responses API structured-output contract using `gpt-5-mini`, prompt `evidence-facts-v4`, and schema `evidence-fact-schema-v2`. Accept high-confidence grounded facts only. Cache by evidence content, relevant target/candidate context, model, prompt, and schema. Preserve source and extraction provenance. Model output may amend normalized evidence facts; it cannot forecast, plan, rank, or validate.

Reason: This confines AI to perception/interpretation while making repeated deterministic evaluation reproducible and inexpensive.

Alternatives considered: Per-sample prompts; free-form advice; live extraction on every run; large regex NLP; treating missing facts as zero.

Consequences: Schema or prompt changes invalidate cache entries. Cached runs make zero model calls and report hits. Low-confidence, malformed, conflicting, wrong-owner, or ungrounded facts fail closed. Percentage amendments and one-occurrence stream amounts remain deterministic downstream fact types rather than model-authored policy.

## Decision: Isolated provisional vertical-slice forecast

Status: Revisit

Superseded in part by deterministic-core-v2 below. The v1 text and baseline remain historical: ignoring explicit terminal payroll and rejecting valid non_cash/lifecycles were incorrect. Recurrence thresholds and ordering remain provisional and unchanged.

Context: The user authorized narrow provisional forecasting after structured-only sample inspection showed that current balance alone could not justify a 90-day prediction.

Decision: **Provisional vertical-slice policy — subject to replacement after evaluator-guided analysis of all solved samples.** Implement `ForecastPolicy -> build_forecast(context) -> ForecastTimeline` separately from loading, decisions, serialization, and validation. Policy `vertical-slice-v1` uses:

- A supplied opening-balance snapshot, past settled events for recurrence only, and an inclusive request-date through request-date + 90 days timeline. Same-day settled source events fail because snapshot timing remains unresolved.
- Structured `(event_type, category, direction)` stream keys; all supplied prior settled observations; at least three observations. Amounts must each be within 35% of the stream median. Forecast maximum observed expense and minimum observed income. Only structured `income/salary` credits are extrapolated.
- Exact 7/10/14/21/28-day intervals, or one/two fixed day-of-month slots repeated identically for at least three consecutive months. Monthly slots after day 28, stale histories, mixed/duplicate dates, singleton streams, and ambiguous patterns fail explicitly.
- Explicit same-stream/same-settlement-date events replace inferred occurrences, including pending credits (which suppress inference but add no cash). Pending debits are reserved at the request date exactly once. A same-stream pending-to-settled lifecycle is supported; other linked lifecycles fail for the future resolver.
- Same-day debits, then candidate payments, then credits, with stable IDs as tie-breaks. Initial balance and every movement are checked; equality with the reserve passes. Decimal arithmetic throughout.
- No evidence interpretation, FX forecasting, optional spending changes, or unresolved-value defaults. The only selected strategy is an eligible fee-free full payment today, and only if simulation proves the entire capped request safe. Unsafe full payment fails rather than fabricating a fallback strategy/status.

Reason: These explicit conservative development conventions complete plumbing without implementing the general financial engine. They are not claimed as organizer-defined estimators or final policy.

Alternatives considered: Current-balance-only decisions (invalid); single-observation salary extrapolation (forbidden); full engine or model interpretation (out of scope).

Consequences: `request_09` runs end to end. `request_01` stays unsupported because it has complex linked lifecycles and only one prior salary observation. One sample match does not validate the policy generally. The 35% band, category-based stream identity, min/max estimators, fixed horizon endpoint, and pending-hold snapshot convention require later evaluation. Development CSVs are staged and independently structurally validated before replacing their output artifact; final root output is protected.

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

Implemented by planning-v1. Immediate capacity is the largest cent-denominated amount proven safe by simulation; earliest full date searches every date through the request-relative horizon and simulates the full remaining timeline. Candidate eligibility precedes ranking. Valid candidates rank by no changes, fewer changes, lower total paid, earlier start, fewer payments, option ID, then a stable method key. No-plan results serialize as `not_affordable`/`not_recommended` rather than an internal unsupported failure.

## Decision: Deterministic planning v1

Status: Accepted

Context: Recurrence-capable requests reached a full-payment-only planner that could neither report safe capacity nor evaluate repository-supported alternatives.

Decision: Generate a finite candidate set from the resolved forecast. Full and wait require accepted full payment; partial uses exactly safe-today plus the remainder on the baseline earliest-full date; installments reproduce supplied options exactly; changes target the latest source event of an eligible recurring stream and affect projected entries only. Enumerate up to three distinct change actions and retain the minimum valid count through ranking. Simulate every candidate and reject deadline, user-preference, duration, schedule, completion, or minimum-balance violations. Interpret `max_installment_months` provisionally as the maximum supplied installment payment count.

Reason: Financial safety and option eligibility are deterministic and auditable once a forecast exists. Raw evidence and recurrence policy do not belong in planning.

Alternatives considered: Static headroom only; invented schedules; model-ranked candidates; modifying raw events for spending changes; emitting unsupported instead of the required no-plan decision.

Consequences: Candidate traces expose method, payments, changes, completion, minimum balance, rejection reason, and rank. `planning-v1-final` processes 6/25 with 19 evidence-stage unsupported cases. Sample differences for requests 01/13/21 are preserved for later forecast-policy analysis; planning did not alter recurrence to match labels. Installment-month interpretation and change effective scope remain provisional.

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

Superseded in part by the recurring-streams-v1 decision below. Amendment duration and final estimator validation remain unresolved.

## Decision: Explicit recurring streams v1

Status: Accepted

Context: Category-only grouping merged distinct salary sources, rejected genuine variable spending, and could extrapolate income after cessation. Singleton investments also reached recurrence logic despite lacking repetition evidence.

Decision: Insert `stream classification -> cadence + continuation + amount policy` between lifecycle reconciliation and forecasting. Fixed transactions use user-scoped type/category/direction/currency plus normalized description. Groceries, transport, and dining are provisional category-level spending-behavior streams because their structured histories deliberately vary merchant labels while retaining a clear cadence. Repeated salary labels remain independent; otherwise three or more variable labels may form an independent day-of-month slot. A singleton is one-time. Two observations or inconsistent cadence are insufficient evidence. Exact 5/7/10/14/21/28-day patterns allow one day of drift; consecutive monthly calendar patterns allow two days. A missed expected occurrence makes continuation insufficient. Exact terminal payroll evidence ends only the uniquely amount/currency-matched salary stream. Explicit future events suppress a same-type/category/direction/currency/date projection.

Reason: Stream identity must use the strongest structured discriminator available without merging broad categories. Continuation, cadence, and amount are distinct questions. Missing income is safely excluded; unresolved recurring debits block forecasting.

Alternatives considered: Broad type/category grouping; exact-description grouping for all behavior; extrapolating singleton events; treating absence as termination; fuzzy LLM classification.

Consequences: Expense amounts use maximum observed and income uses minimum observed, both provisional. Each spending-behavior stream reserves one additional maximum occurrence at the request boundary for timing/count uncertainty. Diagnostics retain source IDs, dates, intervals, cadence, state/reason, estimator, and projections. `recurring-streams-v1-final` keeps v2's 1/25 fully correct processed row and zero comparable mismatches, while recurrence-capable cases now reach planning instead of failing recurrence. These identity rules, tolerance values, behavior-category allowlist, and contingency reserve require further validation.

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

## Decision: Evaluation denominators, isolation, and failure reporting

Status: Accepted

Context: The provisional pipeline supports few samples. Scoring only successful predictions would hide low coverage, while exact prose comparison would penalize equivalent explanations.

Decision: Keep input/answer splitting in `code/evaluation`, pass input-only files to the actual pipeline, and compare serialized predictions afterward. Report six primary financial fields with both all-selected and processed-only denominators. Request ID and prose equality are diagnostics. Missing predictions get explicit missing-field mismatch rows; separate their counts from actual financial mismatches and prose differences. Preserve original exception types and annotate observed pipeline boundaries; use unknown causal stage for output mismatches. Each run uses a new directory with policy/source/data fingerprints and measured usage (currently zero). Future extraction is an application concern; only disabled mode exists now.

Reason: Honest coverage/accuracy reporting, no label leakage, reproducible runs, and no guessed failure causes or official aggregate score.

Alternatives considered: Successful-only accuracy; fabricated fallback predictions for unsupported requests; exact string plan/prose matching; attributing a field mismatch automatically to forecasting.

Consequences: Initial baseline-v1 processes 2/25, with 21 unsupported and 2 normalization failures; only 1/25 fully matches. It records 5 comparable financial mismatches, 138 missing fields and 2 prose diagnostics. Explanation semantic consistency is not assessed; structural validation only requires nonempty prose. Expected-answer mutation and answer-sentinel tests confirm expected outputs cannot affect application predictions. Financial logic was not changed to improve this baseline.

## Decision: Deterministic core v2 reconciliation and terminal income

Status: Accepted

Context: Before code changes, the input-only request_05 trace showed v1 invented three future salary credits of 14740 after an event explicitly described as "Final employer payroll". Opening balance 46475.10 and reserve 13100 yielded v1 baseline minimum 41244.92, headroom 28144.92, capped output 15488, and candidate minimum 25756.92. Trace: `artifacts/diagnostics/request_05-v1/trace.json`.

Decision: Treat the exact normalized description "Final employer payroll" on a settled salary event as an explicit stream-ending fact. The narrow parser does not fuzzy-match arbitrary prose or access messages/images. Later salary records conflict with the marker and remain unresolved without source reconciliation. Do not loosen recurrence/expense thresholds. Under unchanged conservative expenses, removing future salary yields minimum 5317.44 and negative headroom; unsafe immediate payment now fails at planning. The sample's 737 remains unexplained by the current expense policy and is not a tuning target.

Reason: Explicit cessation takes precedence over historical extrapolation; no unsupported future income. The output discrepancy was a recurrence/terminal-state error, not the request cap calculation.

Alternatives considered: Tuning expense estimates to 737; continuing salary from history despite explicit termination; forcing not_affordable without complete planning (all rejected).

Consequences: Deterministic parsing of a narrow event-description marker is supported, not general text extraction. The category-level stream identity is still provisional. Unknown descriptions, multiple employment sources, and later conflicting income need future policy work.

## Decision: Typed non-cash events and explicit lifecycle stage

Status: Accepted

Context: Supplied unrealized investment valuations use event_type=investment_valuation and direction=non_cash. Lifecycle links include authorization/settlement, failed retries, refunds, investments, and unresolved duplicate debits.

Decision: Normalize cash versus informational events explicitly, validate known event-type/direction/status combinations, and reject malformed combinations. Add a separate `reconcile(context) -> ResolvedContext` stage with immutable raw events, effective movements, per-event treatment/source lineage, stream endings and reservation releases. Forecast consumes that result. Supported semantics:

- Failed/cancelled predecessor followed by a same-stream active successor: exclude predecessor and retain successor once.
- Pending to settled: replace the representation once; if settlement is future-dated, preserve at least the old reservation until settlement, releasing a lower final-charge difference only then. A past settlement is already reflected in the opening balance.
- Debit plus refund/reversal: retain distinct movements; unsettled refunds add no cash and do not release the debit. Historical refunds and investment-sale proceeds are not recurring income.
- Investment purchase, valuation and sale: keep genuine cash debit/credit distinct; valuation is informational only.
- A settled debit followed by a potentially duplicate pending debit: no confirmed reversal exists, so retain the additional reservation. Do not delete cash impact based on the link alone.
- Unknown links, cycles, invalid ordering and multiple replacement successors fail explicitly.

Reason: Confirmed repository cash-state/link semantics require both deduplication and preservation of genuinely distinct movements. A link is not an instruction to delete the earlier transaction.

Alternatives considered: Dropping every linked row; ignoring every unfamiliar event; handling replacements opportunistically in forecasting (rejected).

Consequences: Reconciliation and forecast JSON sidecars preserve provenance even when later planning fails. Snapshot/hold timing and conservative same-day ordering remain explicit provisional conventions. The evaluator's baseline-v1 is preserved; v2 removes normalization failures without claiming unsupported requests are solved.

## Decision: Exact FX conversion; defer multi-source salary policy

Status: Accepted

Context: After the first three priorities, request_13 revealed distinct household income streams and a disappearing second stream. Request_25 instead had exact supplied USD-to-IDR rates for historical/confirmed/projected salary settlement dates.

Decision: Add exact Decimal conversion at each movement's settlement date, including inferred future occurrences. Reserve pending debits today using their stated settlement-date rate; keep FX source keys in provenance. Never use event-date/current/reversed/interpolated rates or invent missing future rates. Mixed-currency stream identity remains unresolved. Defer request_13's stream separation and continuation rules.

Reason: FX direction/date lookup is explicitly defined by the repository and can be added independently; household employment continuation requires new policy design.

Alternatives considered: Latest-rate reuse; converting historical salary once then reusing that home-currency amount; loosening salary variation thresholds (rejected).

Consequences: request_25 clears FX support but remains unsupported on transport cadence; no further fix was made. Final v2 run: `artifacts/evaluation/deterministic-core-v2-final/`. 65 tests pass; 25 selected, 1 processed, 24 unsupported, 0 failed, 1 fully matching row. Comparison is preserved at `artifacts/diagnostics/deterministic-core-v2-comparison.json`.

## Decision: Fixed spending remains conservative outside protected categories

Status: Accepted

Context: The forecast used a mean amount for every non-protected expense behavior. That treated records explicitly marked `fixed` as flexible and contributed to unsafe capacity overprediction in request_03 and request_20.

Decision: A recurring expense may use the non-protected mean policy only when its category is unprotected and every source record is explicitly reducible or stoppable. Protected or fixed-source spending uses the conservative observed maximum. This is an amount policy; it does not change cadence or spending-change eligibility.

Reason: Event flexibility is stronger structured evidence than the absence of profile protection. Ignoring `fixed` understates baseline obligations.

Alternatives considered: Continue category-only classification; tune individual amounts; apply the maximum to every expense.

Consequences: All three unsafe overpredictions decrease, but residual overprediction remains and benchmark categorical matches fall by two. The rule is retained for safety and schema consistency. Further changes stop where evidence becomes speculative. Benchmark: `artifacts/evaluation/safety-pass-v1-fixed-streams`; comparison: `artifacts/diagnostics/final-targeted-pass-before-after.csv`.


## Decision: Conservative evidence resolution for production coverage

Status: Accepted

Context: The first production run withheld 55 rows due mostly to missing model targets, uncertain positive cash, malformed extra assertions, two trailing cadence outliers, and one cash-neutral/lifecycle collision.

Decision: Use a repository `related_event_id` only when it identifies one missing-amount event and exactly one untargeted event-scoped amount fact. Treat unconfirmed income/refunds and unposted reversals as no cash contribution or release; retain existing pending debits. Drop unusable model assertions only when another grounded fact or deterministic informational interpretation resolves the evidence. When one of multiple income streams ended but its identity cannot be established, exclude all affected future income from capacity. A long exact cadence may ignore one trailing off-cadence observation. Cash-neutral pairing excludes lifecycle-linked debit/refund pairs.

Reason: These rules use structured relationships and financially conservative uncertainty handling without inventing facts or changing planning/scoring policy.

Alternatives considered: Require the model to repeat linked IDs; count uncertain credits; guess an income-stream identity; relax grounding globally; special-case production request IDs.

Consequences: Cached production coverage increases from 195/250 to 250/250 with zero unsupported/failed rows. All 250 serialized rows pass strict validation; 111 tests and 25/25 sample processing pass. Three missing image cache entries required targeted gpt-5-mini extraction; final cached replay uses zero calls.
