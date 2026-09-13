# Application inference usage report

This report covers the model inference used to populate the evidence cache for the
final 250-request production output. Development work performed in ChatGPT/Codex is
separate and is not included in these application API measurements.

## Final production inference

| Metric | Measured value |
|---|---:|
| Provider | OpenAI |
| Model | `gpt-5-mini` |
| Production requests | 250 |
| Model calls | 159 |
| Calls per request | 0.636 |
| Input tokens | 200,307 |
| Output tokens | 26,368 |
| Total tokens | 226,675 |
| Average tokens per request | 906.7 |
| Retries | 0 |
| Estimated total API cost | USD 0.10281275 |
| Estimated cost per request | USD 0.000411251 |

The measurements combine the initial full production extraction run
`dry-run-v1-live-approved` (156 calls) and the targeted completion run
`blocker-pass-v3-targeted-missing-images` (3 calls). The latter reused 95 valid
cache entries and populated three missing image results. Together these calls
created the evidence cache used for the final output.

The final reproducibility run was
`artifacts/production/blocker-pass-v4-final-cached`. It processed all 250 requests
with **0 model calls**, **96 cache hits**, **0 input/output tokens**, and **USD 0**
incremental API cost. Deterministic parsing handled evidence that did not require
model interpretation, so the cache-hit count is lower than the request count.

Costs are the estimates recorded by the application from measured provider token
usage and the configured `gpt-5-mini` rates at execution time. No unavailable
measurements were fabricated.
