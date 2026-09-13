# Build plan

Current authorization: documentation only. Next milestone is a minimal vertical slice after implementation is authorized. Do not commit or push; the user owns milestone commits.

| Phase | Objective and scope | Success criterion | Dependencies | Major risks |
| --- | --- | --- | --- | --- |
| 1. Architecture/documentation foundation | Record boundaries, tests, tasks, requirements versus assumptions | Four working docs exist; unresolved policies explicit | Repository analysis | Treating proposals as confirmed rules |
| 2. Minimal vertical slice | Select 1–2 simple samples; load, build context, normalize structured facts, minimal deterministic processing, serialize, validate shape | Selected inputs traverse the real boundaries; provisional result clearly identified | Phase 1; implementation authorization | Mistaking plumbing for financial correctness; sample-label leakage |
| 3. Evaluation harness | Smoke/all-sample runner, isolated labels, field metrics, mismatches, manifests, configuration comparison and cache/usage interfaces | Predictions are compared reproducibly; deliberate mismatch detected | Phase 2 | Misleading numeric/text comparisons; absent failure traces |
| 4. Deterministic financial engine | Resolve events, policy-driven recurrence, FX, ordered forecast, baseline capacity | High-value unit tests pass; calculations explainable through traces | Phase 3; relevant policy decisions | Double counting; unsupported recurrence; temporal ambiguity |
| 5. Expanded end-to-end pipeline | Eligible candidates, spending changes, simulation, ranking, independent validation | Structured cases produce validated decisions across supported methods | Phase 4 | Wrong eligibility, deadlines, partial-payment semantics |
| 6. Selective AI/image extraction | Narrow contract, reviewed cases, provenance, cache, bounded errors, usage capture | Relevant unstructured facts enter resolver through validated boundary | Phase 5; model configuration | Wrong field/temporal scope; invented facts; variable extraction |
| 7. Full sample benchmark | Run all 25 solved samples with frozen configuration | Complete per-field metrics, mismatch and safety reports | Phase 6 | Confusing benchmark fit with general correctness |
| 8. Failure analysis | Classify mismatches by earliest faulty stage; minimize regressions | Material failures have evidence and prioritized causes | Phase 7 | Blaming extraction for deterministic bugs or vice versa |
| 9. Targeted improvements | Fix general high-impact causes and rerun focused/full checks | Improved metrics with no safety regressions or ID-specific rules | Phase 8 | Overfitting; unbounded iteration |
| 10. Full dataset run | Freeze configuration; process 250 evaluation requests and retain usage/traces | All requests handled; no unresolved material failures | Phase 9 | Runtime/cost surprises; stale caches |
| 11. Final output validation | Re-read output; verify exact schema/coverage and financial/plan constraints | Independent release checks pass | Phase 10 | Serialization drift; validating only in-memory results |
| 12. Submission/documentation preparation | Reproducible run instructions, package, transcript, usage report | Required artifacts complete and runnable; no secrets | Phase 11 | Wrong archive paths; missing usage attribution; time pressure |

Phase 2 proves plumbing and architecture, **not full financial correctness**. Do not present provisional predictions as final output. Development order remains vertical slice -> evaluator -> financial engine -> expanded pipeline -> AI extraction.

## Evaluation milestones

- Fast loop: fixed small sample subset plus targeted deterministic tests.
- Milestone loop: all 25 samples, per-field metrics/mismatches, safety failures, configuration fingerprint.
- Failure loop: focused regression before a fix, then relevant tests and full benchmark when warranted.
- Extraction loop: reviewed facts and frozen cache; compare deterministic configurations against identical facts.
- Release loop: full dataset and independent serialized-output validation; actual model usage and cached-origin usage clearly distinguished.

Timebox phases 8–9 and preserve time for phases 10–12. Update this plan only if milestones or sequencing change.
