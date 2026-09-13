# Local sample evaluation

From the repository root (Python 3.10+, standard library only):

```bash
python3 -B code/evaluation/main.py --request-id request_09
python3 -B code/evaluation/main.py --request-id request_09 --request-id request_01
python3 -B code/evaluation/main.py --subset smoke
python3 -B code/evaluation/main.py --all
python3 -B -m unittest discover -s tests -v
```

Each invocation creates a unique `artifacts/evaluation/<run-id>/` directory.
An optional `--run-id NAME` names a run but never overwrites an existing directory.
`--policy-config FILE.json` supplies explicit `ForecastPolicy` overrides for separate
configuration comparisons; this baseline uses the unchanged default policy.

## Boundaries and artifacts

`samples.py` splits input and answer dictionaries before application ingestion.
Only exact input columns are written to each `requests/<ordinal>/input.csv`.
The real application pipeline receives that file, the dataset path, policy, and
output path. Answers remain in the evaluator and are compared only after the
pipeline finishes. No application module imports evaluation code.

- `predictions.csv`: successfully generated and structurally validated rows only.
- `metrics.json`: counts, per-field accuracy, matching rows, mismatch breakdowns.
- `mismatches.csv`: expected/actual values, semantic differences, stage/diagnostic.
- `request_results.json`: one outcome per selected request, including failures.
- `metadata.json`: selection, timestamp, policy/config hash, local Git revision,
  Python source hash and dataset hash. No environment/secrets are read.
- `usage.json`: measured usage foundation; currently zero calls/tokens/cost/cache
  activity with an empty provider/model record list.

Each request fails independently. Original exception types are retained;
application boundary annotations distinguish loading, context, normalization,
forecast, planning, serialization and validation. A mismatch alone does not
establish causality, so its causal stage is `unknown`. Forecast may reject evidence
or lifecycle records internally; these are observed forecast-stage failures,
not claimed extractor/resolver execution.

## Comparison and metric definitions

- Six primary financial fields: amount, status, method, plan, earliest date, changes.
- Monetary comparison uses Decimal equality and exact absolute error strings.
- Dates compare parsed ISO dates; signed difference is actual minus expected.
  Blank versus present is reported separately, not as a fabricated day error.
- Plans compare chronological payment tuples; `10` equals `10.00`. Payment count
  is preserved; separate installments are not combined. Changes compare unordered
  normalized actions with duplicate targets rejected.
- Categorical fields use whitespace-trimmed, case-sensitive equality.
- Request ID is a separate alignment diagnostic. Explanation equality is exact
  and diagnostic-only. Prose semantic consistency is explicitly `not_assessed`;
  existing structural validation requires a nonempty explanation. No LLM judge.
- Report accuracy over **all selected requests** and **processed requests only**.
  No prediction counts as unmatched in the first denominator and is excluded from
  the second. Zero processed requests yields null conditional accuracy.
- Fully matching rows match all six primary fields. Explanation wording never
  reduces that count.
- `total_mismatch_count` counts artifact rows, including six missing-field entries
  per unsupported/failed request and diagnostic prose/ID differences. Separate
  counts expose actual comparable mismatches versus missing predictions.
- These are development measurements, not an official HackerRank score.

## Extraction compatibility

The current pipeline uses no extraction. `UsageLedger` accepts measured provider,
model, token/call, retry/cache and optional cost records for later integration.
An unknown nonzero-call cost remains null, never zero. The current empty ledger
truthfully totals zero. Only extraction mode `disabled` is supported today;
future `live`/`cached` implementations can feed the same application contracts
without changing comparison logic. Unsupported modes fail rather than pretending
to use a model or cache. The final-submission `usage_report.md` remains a later artifact.

## Initial unchanged-policy baseline

Runs: `smoke-v1` and `baseline-v1`, policy `vertical-slice-v1`.

| Measure | Smoke | All samples |
| --- | --- | --- |
| Selected | 2 | 25 |
| Processed | 1 | 2 |
| Unsupported | 1 | 21 |
| Failed | 0 | 2 |
| Fully matching structured rows | 1 | 1 |

Full baseline: five fields match 1/25 (4% overall, 50% among predictions).
`spending_changes_needed` matches 2/25 (8% overall, 100% among predictions).
There are 5 comparable financial mismatches, 138 missing financial fields, and
2 prose diagnostics: 145 total mismatch rows. No model calls/tokens/cost.

`request_05` is a false-positive affordability result relative to the sample:
safe amount 15488 versus 737 (absolute error 14751), and different status, method,
plan and earliest date. The causal forecasting/accounting issue is not established
by these output comparisons alone. `request_09` matches all six primary fields.

Observed blockers: 18 uninterpreted-evidence cases, 1 unsupported linked lifecycle,
1 variable salary recurrence, 1 unsupported FX forecast, and 2 normalization
failures rejecting `direction=non_cash` on unrealized investment valuations.
These are measurements only; no financial failures were patched for this run.
