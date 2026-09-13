# Documentation Review 07: Selective AI Extraction and Cache Replay

**Repository:** HackerRank Orchestrate - Buy or Wait?  
**Review date:** 2026-09-13  
**Scope:** AI extraction, deterministic-first evidence handling, versioned cache,
replay mode, provenance, usage accounting, tests, and the cached 25-sample
benchmark. This review is advisory; no code or existing documentation was
changed.

## 1. Executive assessment

The extraction milestone is substantially complete as an engineering feature.
It introduces a narrow evidence-to-facts contract rather than allowing a model
to make financial decisions. The pipeline validates structured facts, grounds
them to supplied evidence and event IDs, applies only typed event amendments,
records provenance, and supports live extraction followed by zero-call cached
replay.

The cached verification run is particularly valuable: **24/25 samples
processed, 0 failed, 1 forecast-unsupported**, with **10 cache hits and zero
model calls/tokens/cost** in the replay run. This demonstrates that the
extraction boundary can be replayed deterministically without paying for or
repeating model calls.

The milestone is not fully submission-ready yet. The benchmark has only 1/25
fully matching structured rows and 90 comparable structured mismatches. Most
remaining discrepancies are downstream forecast/capacity policy issues, which
is expected after extraction. The largest documentation/release gap is that the
required submitted `evaluation/usage_report.md` is still empty, while run-level
`usage.json` now contains useful cache/provider/model records.

**Current maturity:** strong selective extraction and replay foundation; final
accuracy, usage-report packaging, cache integrity, and full-dataset release
validation remain.

## 2. Validation and benchmark evidence

The final cached artifact
`artifacts/evaluation/selective-extraction-v2-final-cached-verified/` reports:

| Measure | Result |
|---|---:|
| Solved samples selected | 25 |
| Processed | 24 |
| Forecast-unsupported | 1 |
| Failed | 0 |
| Fully matching structured rows | 1 |
| Comparable structured mismatches | 90 |
| Missing prediction fields | 6 |
| Cache hits | 10 |
| Model calls | 0 |
| Input/output tokens | 0/0 |
| Estimated replay cost | 0 |

This is a major coverage improvement from the planning phase’s 6/25 processed
requests. The replay result supports the claim that cached extraction avoids
new model calls. It does not prove that the cached facts are correct, only that
the same cached facts can be reused consistently.

## 3. What was completed well

### 3.1 Narrow model responsibility

The prompt explicitly prohibits affordability decisions, balance forecasting,
payment recommendations, policy invention, and unsupported inference. The
model returns typed evidence facts; deterministic reconciliation, forecasting,
planning, and validation remain outside the model.

### 3.2 Strict schema and grounding

The schema restricts fact types, scope, targets, dates, directions, confidence,
and evidence text. Image extraction is constrained to one amount fact for the
target event. Message facts are grounded against message text, and event
references are checked against the request user’s event set.

### 3.3 Deterministic-first extraction

Known message patterns are handled without a model. This reduces cost and
variance while keeping the model boundary for heterogeneous evidence.

### 3.4 Versioned cache identity

Cache keys incorporate evidence content, source context, model, prompt version,
schema version, and candidate targeting context. Cache version mismatches fail
closed instead of silently reusing stale facts.

### 3.5 Replay accounting is honest

The verified cached run reports provider/model identity, ten cache hits, zero
model calls, zero tokens, and zero replay cost. This is materially better than
claiming that cached replay had no originating extraction cost.

### 3.6 Controlled failures remain visible

Cache misses in cached mode and unresolved/low-confidence extraction results
remain unsupported rather than becoming `not_affordable`. This preserves the
financial safety boundary.

## 4. Findings

### F-01 — Critical: the required submitted usage report remains empty

The run-level `usage.json` is informative, but
`code/evaluation/usage_report.md` is still empty. The challenge requires a
Markdown usage report in the submitted code package covering the final
full-dataset run, providers/models, calls, input/output tokens, averages, and
estimated cost.

**Recommendation:** Generate the Markdown report from the authoritative final
run ledger. Include current-run usage and cached-origin usage separately:

```text
final run requests
current model calls/tokens/cost
cache hits/misses
originating extraction calls/tokens/cost for reused facts
average tokens/request
pricing basis and unknown-cost handling
```

Do not report replay cost as the total historical extraction cost.

### F-02 — High: sample benchmark accuracy remains low after extraction

The cached run processes 24/25 requests, but only 1/25 fully matches all six
structured fields. Amount accuracy is 1/25 overall and 1/24 among processed
requests; status, method, plan, and earliest date are 8/25 overall. Spending
changes are stronger at 21/25 overall.

**Recommendation:** Treat extraction coverage as successful, but do not conflate
it with financial correctness. The next work should analyze deterministic
forecast/capacity mismatches using extracted facts frozen, so model variance is
not mixed with downstream policy changes.

### F-03 — High: cache integrity is versioned but not authenticated

Cache files contain prompt/schema versions and results, but there is no
content hash or signature over the cache payload. A modified cache file with the
same versions could be replayed if its schema remains valid.

**Recommendation:** Store a canonical payload hash and verify it before replay.
For stronger release integrity, include a cache manifest with file hashes,
dataset/source fingerprints, creation run, provider/model, and schema versions.
Treat tampered or partially written entries as cache misses/errors.

### F-04 — High: live-to-cache provenance does not yet clearly distinguish source cost

Each cached hit records zero current-run calls and cost, which is correct. The
artifact should also identify the origin run and original model usage for each
cache entry, otherwise the final package may understate total extraction cost.

**Recommendation:** Add `origin_run_id`, origin timestamp, origin provider/model,
origin input/output tokens, and origin estimated cost to each cache record or
manifest. Aggregate both current-run and origin-attributed totals.

### F-05 — High: evidence selection includes broad candidate context

The extraction payload includes request context and candidate event metadata.
Although the prompt says candidate fields are not evidence, broad candidate
lists can increase prompt size, cost, and accidental target association.

**Recommendation:** Make candidate selection relevance-scoped and bounded.
Record why each candidate was included, reject facts targeting candidates not
authorized by the source relationship, and test near-duplicate candidate
ambiguity. Do not send unnecessary profile or event data to the provider.

### F-06 — Medium: model response validation should enforce provider response limits

The extractor validates JSON schema-like fields after parsing, but the response
path does not document maximum fact count, evidence fragment length, response
size, or retry/backoff behavior. A valid but excessive response could inflate
diagnostics and downstream processing.

**Recommendation:** Define bounded response limits, explicit timeout/retry
policy, and provider error categories. Preserve original failure metadata
without logging secrets or full sensitive prompts.

### F-07 — Medium: fact conflict resolution is narrower than the challenge conflict rules

Conflicting extracted amounts are rejected, which is safe. However, the
documentation should explicitly state how multiple high-confidence facts from
different sources are resolved when one is newer, settled, amended, or
cancelled. The challenge has a published precedence order that must remain
deterministic.

**Recommendation:** Keep extraction as assertions only and implement all
cross-source precedence in reconciliation. Add fixtures for amendment,
cancellation, newer-source, settled-versus-estimate, and unresolved conflicts.

### F-08 — Medium: cache replay tests should verify semantic equivalence, not only zero calls

The verified run establishes zero calls and ten hits. It should also compare
live-origin and cached-replay normalized facts, resolved contexts, forecast
diagnostics, and serialized predictions byte-for-byte or semantically.

**Recommendation:** Add a replay equivalence artifact with source/configuration
fingerprints and hashes for extracted facts, predictions, and key diagnostics.
A cache replay that changes a fact should fail the verification gate.

### F-09 — Low: extraction metadata is not yet in the final package contract

The application writes extraction diagnostics relative to the output directory,
but the evaluator artifact contract does not yet clearly require extraction
fact manifests, cache keys, provenance, or origin usage records.

**Recommendation:** Extend the run manifest to include extraction mode,
prompt/schema versions, cache hit/miss counts, cache manifest hash, and
per-request extraction outcome.

## 5. Phase verdict

| Dimension | Verdict |
|---|---|
| AI boundary design | **Strong** |
| Evidence grounding | **Strong foundation** |
| Deterministic-first behavior | **Good** |
| Cache replay | **Demonstrated** — 10 hits, zero calls in verified replay |
| Usage attribution | **Partially complete** — machine ledger exists; submitted Markdown report absent |
| Benchmark coverage | **Strong improvement** — 24/25 processed |
| Financial accuracy | **Still limited** — 1/25 fully matching |
| Submission readiness | **Not ready** — usage package, full dataset, and downstream mismatches remain |

## 6. Prioritized next steps

### P0 — release accounting and replay integrity

- Generate nonempty `evaluation/usage_report.md` from the authoritative final run.
- Separate current replay usage from originating cache extraction usage.
- Add cache payload hashes and a cache manifest.
- Add live-versus-cached semantic replay equivalence verification.

### P1 — downstream deterministic correctness

- Freeze extracted facts and analyze forecast/capacity mismatches.
- Resolve request_17 duplicate-date spending behavior.
- Revisit amount-safe capacity and recurring expense policy without changing
  extraction contracts.
- Add independent post-serialization safety validation.

### P2 — final release

- Run the 250-request pipeline with cache/evidence manifests.
- Validate output coverage, payment schedules, minimum-balance safety, and
  spending-change eligibility independently.
- Package code, output, transcript, usage report, cache policy, and checksums
  without secrets or prohibited files.

## 7. Recommended next-milestone acceptance criteria

- [ ] Cached replay produces the same normalized facts and predictions as the
  live-origin run.
- [ ] Cache entries have verified payload hashes and origin metadata.
- [ ] Usage report is nonempty and distinguishes replay from origin cost.
- [ ] All 25 samples are either processed or have a documented, stable blocker.
- [ ] Downstream mismatch analysis uses frozen extracted facts.
- [ ] At least one extraction-dependent image case and one message amendment
  case pass independent safety validation.
- [ ] No provider credentials, raw secrets, or unnecessary sensitive evidence
  are included in artifacts.
