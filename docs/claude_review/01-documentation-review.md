# Documentation Review 01: Industrial Standards and Hackathon Compliance

**Repository:** HackerRank Orchestrate - Buy or Wait?  
**Review date:** 2026-09-13  
**Reviewer:** Claude consultant review  
**Scope:** Documentation only. No existing repository files were changed.

## 1. Executive assessment

The repository has a sound documentation foundation for a hackathon prototype. The
best parts are the explicit separation between AI perception and deterministic
financial reasoning, the emphasis on Decimal arithmetic and provenance, the list
of financial invariants, and the phased delivery plan. These choices are aligned
with the challenge rules and are materially safer than an LLM-generated financial
decision.

The documentation is not yet at an industrial standard for a production-like
decision service or an auditable competition submission. The main weaknesses are:

1. Requirements, design decisions, risks, and implementation evidence are mixed
   without stable identifiers or a traceability matrix.
2. Several decisions that can change hidden-test outcomes remain unresolved, while
   the plan moves toward implementation.
3. There is no complete data dictionary, machine-checkable output contract,
   interface/version contract, threat model, operational runbook, or release
   evidence.
4. The documentation does not yet prove that the documented architecture is
   implemented, tested, packaged, and reproducibly runnable.
5. The submission and transcript requirements are described, but ownership,
   generation commands, validation evidence, and final artifact checks are not
   documented as a release procedure.

**Overall rating:** Good architecture notes; incomplete requirements and release
documentation. Suitable for continuing design work, not yet sufficient as a
production-grade or submission-ready documentation set.

## 2. Documents reviewed

| Document | Assessment |
|---|---|
| [README.md](../../README.md) | Good onboarding and challenge summary; needs a verified end-to-end runbook and artifact checklist. |
| [problem_statement.md](../../problem_statement.md) | Primary challenge contract; useful and detailed, but should be treated as an immutable source specification and referenced by requirement IDs. |
| [AGENTS.md](../../AGENTS.md) | Strong agent operating rules, logging, safety constraints, and project contract; needs a concise human-facing cross-reference rather than being the only process source. |
| [CLAUDE.md](../../CLAUDE.md) | Correctly delegates to `AGENTS.md`; offers little discoverability for non-Claude contributors. |
| [docs/design.md](../design.md) | Strong architectural boundary and invariants; some content is still conceptual and some decisions are described as accepted before implementation evidence exists. |
| [docs/decisions.md](../decisions.md) | Good lightweight ADR-style record; needs IDs, dates, owners, alternatives, validation evidence, and explicit supersession links. |
| [docs/plan.md](../plan.md) | Sensible staged plan and risks; needs measurable exit criteria, owners, dependencies, and links to tests/artifacts. |
| [docs/tasks.md](../tasks.md) | Useful current-state tracker; should distinguish blocked product decisions from implementation tasks and retain completion evidence. |
| [code/evaluation/usage_report.md](../../code/evaluation/usage_report.md) | Required artifact is represented; it must be populated from the actual final run and linked to a run manifest. |

## 3. Comparison with the hackathon requirements

### 3.1 Covered well

- The required root-level `output.csv`, exact eight-column order, and one-row-per-
  request requirement are stated in the README, problem statement, and
  `AGENTS.md`.
- The required status and payment-method values are documented.
- The partial-payment rule is captured, including exactly two payments, positive
  initial payment, completion by the desired date, and sum-to-requested-amount.
- Installment schedules are required to match supplied options.
- The 90-day safety rule, minimum balance protection, pending-credit exclusion,
  unrealized-investment exclusion, settlement-date FX, and conflict precedence
  are explicitly documented.
- Evidence handling is appropriately safety-oriented: blank amounts are not zero,
  images/messages are untrusted, and embedded instructions cannot override rules.
- The required `evaluation/usage_report.md`, model/token/cost fields, and
  no-secrets rule are visible.
- The plan explicitly separates sample answers from the prediction pipeline, which
  reduces label leakage risk.

### 3.2 Requirements that are documented but not yet evidenced

The documents state these requirements, but no evidence is linked showing that
they work:

- Terminal execution from a clean checkout.
- Correct loading and joining of every participant-facing CSV.
- Image extraction for all blank financial-event amounts.
- Correct handling of lifecycle links, cancellations, amendments, pending records,
  recurring events, and foreign-currency events.
- Exact plan arithmetic and eligibility validation.
- Independent validation after serialization, not only in-memory validation.
- Complete output coverage for all 250 evaluation requests.
- A final usage report corresponding to the exact run that produced `output.csv`.
- A reproducible `code.zip` containing the required evaluation directory and
  setup instructions.

The documentation should link each claim to a command, test, fixture, run
manifest, or retained report. A statement of intent is not acceptance evidence.

### 3.3 Ambiguities that can affect compliance

These are correctly identified in [decisions.md](../decisions.md), but must be
resolved before the financial engine is considered complete:

- Whether the profile balance is already a request-date snapshot and how pending
  holds interact with it.
- Whether the 90-day horizon includes the boundary day.
- Ordering of same-day income, expenses, and requested payments.
- Historical window and estimator for recurring and variable essential spending.
- Effective duration of temporary versus recurring amendments.
- Mapping of `max_installment_months` to supplied day intervals.
- Output status when a safe plan exists only after the desired completion date.
- Effective date and target event for recurring spending changes.
- Decimal quantization, currency precision, and tie-breaking of option IDs.
- Attribution of current-run usage versus the cost of evidence in a reused cache.

These should be recorded as explicit, versioned policies with boundary fixtures;
they should not remain informal implementation choices.

## 4. Industrial-standard assessment

### 4.1 Requirements engineering: **Partially meets**

**Strengths**

- The primary challenge specification is centralized.
- Safety invariants and permitted values are explicit.
- The plan recognizes the difference between requirements and assumptions.

**Gaps**

- No stable requirement IDs such as `REQ-OUT-001` or `SAFE-FX-002`.
- No traceability from each requirement to design component, test, and release
  evidence.
- No formal acceptance criteria for explanations, unresolved evidence, or
  usage accounting.
- No change-control policy identifying which document is authoritative when the
  README, problem statement, and agent contract diverge.

**Recommended change**

Create `docs/requirements.md` with one row per requirement:
`ID | source | normative statement | priority | component | test | evidence |
status`. Keep the challenge statement unchanged; use the matrix to track
implementation.

### 4.2 Architecture and design: **Mostly meets**

**Strengths**

- The pipeline boundary is clear and appropriately deterministic.
- Provenance, cache versioning, normalized facts, and validator boundaries are
  good architectural decisions.
- The design explicitly prevents AI from inventing financial assumptions or
  overriding hard constraints.

**Gaps**

- No context/container diagram showing files, process boundaries, model provider,
  cache, output, and evaluator.
- No sequence diagram for one request.
- No versioned schemas for normalized facts, candidate plans, traces, or usage
  records.
- No explicit failure taxonomy or retry/timeout/circuit-breaker policy for model
  calls and image extraction.
- No data retention/deletion policy for extracted evidence and prompts.

**Recommended change**

Add `docs/architecture.md` with diagrams, component responsibilities, data
contracts, trust boundaries, and failure behavior. Add JSON Schema or typed
contract definitions for every persisted/inter-component object.

### 4.3 Decision records: **Partially meets**

The decisions document is a useful ADR seed, but industrial ADRs normally include
an ID, status, date, decision owner, context, decision, consequences,
alternatives, validation evidence, and supersession history.

**Recommended change**

Convert each entry to an ADR with IDs (`ADR-001`, etc.), dates, status values
(`proposed`, `accepted`, `deprecated`, `superseded`), and links to the tests or
fixtures that validate it. Rename “Accepted” decisions that have no
implementation evidence to “Accepted design policy” or add evidence.

### 4.4 Testing and quality evidence: **Does not yet meet**

The design lists excellent testing categories, but the repository documentation
does not identify the test runner, test locations, test commands, coverage
expectations, golden-fixture policy, mutation/adversarial checks, or the actual
results of any run.

**Recommended change**

Add `docs/testing.md` covering:

- fast unit and schema checks;
- sample benchmark and per-field metrics;
- adversarial evidence and prompt-injection fixtures;
- regression fixture format;
- independent serialized-output validation;
- deterministic seed/configuration requirements;
- minimum release gates and retained artifacts.

Each completed plan phase should link to a dated test report, not only a checked
box in `tasks.md`.

### 4.5 Security, privacy, and responsible financial behavior: **Partially meets**

The untrusted-evidence and no-secrets rules are strong. However, there is no
threat model for prompt injection, malicious image text, data exfiltration,
provider logging, dependency compromise, or accidental inclusion of the
gitignored transcript in code artifacts. There is also no privacy classification
for financial events, messages, images, prompts, caches, or logs.

**Recommended change**

Add `docs/security-and-privacy.md` with:

- assets and data classification;
- trust boundaries and threat actors;
- prompt/image injection controls;
- secret and PII handling;
- model-provider data-sharing assumptions;
- cache/log retention and redaction;
- dependency and archive inspection;
- security release gates.

Do not put raw sensitive evidence or model prompts into ordinary logs.

### 4.6 Reproducibility and operations: **Does not yet meet**

The plan mentions fingerprints, cache origin, usage, and final validation, but
there is no reproducibility contract or operational runbook.

**Recommended change**

Add `docs/runbook.md` specifying:

1. environment and dependency setup;
2. exact command to run from repository root;
3. configuration and environment variables;
4. cache behavior and how to force a clean run;
5. expected input/output counts;
6. validation commands;
7. failure diagnosis and recovery;
8. packaging and archive inspection;
9. final artifact checksums and run manifest.

The final run should record code commit/hash, dataset fingerprint, configuration
fingerprint, model/provider, cache state, start/end time, exit status, and output
row count.

### 4.7 Documentation usability and maintenance: **Partially meets**

The documents are readable and generally concise. The plan/tasks split is useful.
However, there is no documentation index, glossary, ownership model, version/date
metadata, link-check policy, or definition of done for documentation changes.

**Recommended change**

Add `docs/README.md` as an index, with audience and authority ordering. Add
front matter or a small metadata block to maintained documents:
`status | owner | last reviewed | source of truth | next review`. Add a link
check and documentation review to the release checklist if the repository
supports CI.

## 5. Specific inconsistencies and risks to correct

1. **Authority is unclear.** The README, problem statement, and `AGENTS.md`
   repeat overlapping rules. State that `problem_statement.md` is the challenge
   contract, `AGENTS.md` is the agent/process contract, and README is onboarding.
2. **“Accepted” versus “unresolved” needs sharper semantics.** Accepted
   architecture choices and accepted challenge requirements should not be mixed
   with policies still awaiting fixtures or implementation evidence.
3. **Implementation status is easy to misread.** `design.md` says implementation
   has not started, while the presence of evaluation files and a usage-report
   path can imply otherwise. Add an explicit implementation status and generated
   artifact status.
4. **The required output is called “eight columns” in places, but the challenge
   contract should be mechanically checked.** Document the canonical header in one
   place and link to it.
5. **Sample benchmark language should state that sample outputs are evaluator
   inputs only.** The existing decision is correct; make the prohibition visible
   in the runbook and evaluator contract.
6. **Evidence failure behavior needs a release policy.** “Block final artifact”
   is safe, but specify whether the run exits nonzero, which report records the
   unresolved facts, and how a human resolves them.
7. **The usage report needs a schema.** Define the units, pricing source/date,
   cache-origin attribution, rounding, and treatment of retries.
8. **No explicit dataset integrity gate exists.** Before inference, validate
   required files, headers, unique IDs, referential integrity, dates, currencies,
   image presence, and supplied installment sums.
9. **No explicit dependency/runtime support statement exists.** A clean-machine
   run needs a supported Python version, dependency lock strategy, and offline
   versus network behavior.
10. **No final packaging inspection is specified.** The runbook should verify
    archive contents, exclude secrets and unnecessary raw data, and include the
    required evaluation report.

## 6. Prioritized change backlog

### P0 - before implementing the full financial engine

- Resolve and version all policies listed in section 3.3.
- Add requirement IDs and a requirements-to-tests traceability matrix.
- Define schemas for normalized facts, forecasts, candidate plans, traces, and
  usage records.
- Add dataset-integrity and output-contract acceptance criteria.
- Define same-day ordering, decimal precision, horizon boundaries, and
  installment eligibility with boundary fixtures.

### P1 - before the first credible benchmark

- Add the architecture/context and request sequence diagrams.
- Add the testing strategy and evaluator contract.
- Add deterministic failure taxonomy and evidence-resolution behavior.
- Implement and document the reproducible run command, clean-run procedure, and
  run manifest.
- Record benchmark results by field, safety failures, unresolved facts, and
  configuration fingerprint.

### P2 - before final submission

- Populate `evaluation/usage_report.md` from the exact final full-dataset run.
- Add security/privacy review and archive inspection.
- Add final release checklist covering output schema, 250-row coverage, bounds,
  payment schedules, flexible-only changes, no secrets, and `code.zip`.
- Add documentation index, ownership, review dates, and authority ordering.
- Preserve the final transcript and ensure it contains no secrets or unnecessary
  sensitive evidence.

## 7. Suggested release acceptance checklist

The following should become a checked, retained artifact for the final run:

- [ ] Clean environment setup succeeds from documented instructions.
- [ ] Dataset integrity checks pass without organizer-only inputs.
- [ ] Every evaluation `request_id` appears exactly once in root `output.csv`.
- [ ] Header order exactly matches the challenge contract.
- [ ] Amount bounds and Decimal/rounding checks pass.
- [ ] Every plan is chronological, arithmetically valid, and deadline-safe.
- [ ] Installments match an eligible supplied option exactly.
- [ ] Spending changes are at most three and target only eligible flexible events.
- [ ] Minimum-balance safety is independently simulated from serialized output.
- [ ] No material unresolved evidence remains.
- [ ] Sample benchmark, regression suite, and adversarial checks pass.
- [ ] Usage report matches the final run, including cache-origin attribution.
- [ ] `code.zip` contains runnable code, instructions, evaluation report, and no
  secrets or prohibited organizer-only files.
- [ ] Transcript is complete, redacted, and packaged as required.
- [ ] Final run manifest and checksums are retained.

## 8. Recommended documentation target state

The minimum industrial-quality set should be:

```text
docs/
  README.md                    # documentation index and authority order
  requirements.md              # IDs and traceability
  architecture.md              # diagrams and interfaces
  design.md                    # implementation design
  decisions.md                 # ADRs
  testing.md                   # test/evaluation strategy and evidence
  security-and-privacy.md      # threat model and data handling
  runbook.md                   # setup, run, diagnose, package
  release-checklist.md         # final acceptance gates
  plan.md                      # milestones
  tasks.md                     # current actionable work
  claude_review/
    01-documentation-review.md
```

Do not create all of these files speculatively if time is constrained. Create
them in the P0/P1/P2 order above, and keep every document linked to a concrete
implementation or retained verification artifact.
