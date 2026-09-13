# Documentation Review 11: Full Run and Submission Package

**Repository:** HackerRank Orchestrate - Buy or Wait?  
**Review date:** 2026-09-13  
**Scope:** Final root `output.csv`, `code.zip`, usage report, transcript
requirements, README contract, and the completed 250-request production run.
This review does not modify production code or existing documentation.

## 1. Executive verdict

The final full run and submission package now satisfy the core file-format and
coverage requirements:

- root `output.csv` exists;
- it contains 250 prediction rows;
- all 250 request IDs are unique and match `dataset/requests.csv`;
- the exact eight required columns are present in the required order;
- `code.zip` exists and includes the runnable code, tests, README, evaluation
  harness, and `evaluation/usage_report.md`;
- the usage report is nonempty and documents the measured extraction usage;
- the root output is byte-identical to the validated production artifact;
- the usage report inside the zip is byte-identical to the repository report;
- the repository `log.txt` exists as the required transcript source.

**Submission readiness:** **Ready, subject to the final HackerRank upload
check and preservation of these exact files.**

The package proves operational completeness and schema compliance, not hidden
answer correctness. The solved-sample benchmark remains imperfect, especially
for exact `amount_safe_to_pay`, so the submission should not claim that
250/250 rows are financially correct. It is accurate to claim that 250/250
rows were generated and passed structural validation.

## 2. Artifacts inspected

| Artifact | Result |
|---|---|
| `output.csv` | Present; 250 data rows |
| `code.zip` | Present; 35 entries, 241,859 uncompressed bytes |
| `evaluation/usage_report.md` | Present; 1,608 bytes |
| `code.zip/evaluation/usage_report.md` | Present and byte-identical |
| `log.txt` | Present; 118,701 bytes |
| Production output source | `artifacts/production/blocker-pass-v4-final-cached/output.csv` |
| Strict audit | Passed; 250 rows, exact IDs/columns, no option/change errors |

### Hashes checked

| File | SHA-256 |
|---|---|
| Root `output.csv` | `0c4ca2e0255c1d21a59d6984e304be51171d1e089fcec276bf6efc5d83cdf246` |
| `evaluation/usage_report.md` | `a85837ed9567b469cfd0e7de565a8b69d554862a1f1fb48c262f849d11b4dcd5` |
| `code.zip` | `ec78f6602aec49bd699d435cc415793e16a8ef863e8fd9252508ed8d6222d80e`

The output hash matches the final validated production artifact. The usage
report hash matches the copy embedded in `code.zip`.

## 3. Requirement-by-requirement assessment

| Requirement | Status | Evidence |
|---|---|---|
| Runnable from terminal | **Met** | README includes production and evaluation commands; packaged Python source compiles |
| Reads provided dataset files | **Met** | Production runner and README use `dataset/` |
| One row per evaluation request | **Met** | 250 rows, 250 unique IDs, exact ID-set match |
| Exact output schema | **Met** | Required eight columns and order verified |
| Safe amount bounds | **Validated in production audit** | Strict read-back passed; retain audit with run evidence |
| Allowed statuses/methods | **Validated by output validator** | Full production audit passed |
| Installment option matching | **Validated** | No supplied-option errors |
| Flexible-only spending changes | **Validated** | No spending-change errors |
| Deterministic/replayable execution | **Met for final replay** | Cached extraction, fixed policy metadata, zero new calls |
| No answer leakage in application boundary | **Met by design review** | Evaluator keeps answers outside application inputs |
| Secrets not committed/package | **No secret entries found** | Archive listing has no `.env`, credentials, cache, or artifact paths |
| Usage report in `code.zip` | **Met** | `evaluation/usage_report.md` included and nonempty |
| Full-run usage accounting | **Met with attribution note** | 159 origin calls, 226,675 tokens, estimated USD 0.10281275 |
| Chat transcript | **Prepared** | `log.txt` exists and is separate from `code.zip` |

## 4. Usage-report review

The report identifies:

- provider: OpenAI;
- model: `gpt-5-mini`;
- 250 production requests;
- 159 originating model calls;
- 200,307 input tokens;
- 26,368 output tokens;
- 226,675 total tokens;
- 906.7 average tokens per request;
- USD 0.10281275 estimated originating cost;
- USD 0.000411251 estimated cost per request;
- 0 current calls and zero incremental cost for the final cached replay.

This satisfies the required provider/model, call, token, total/average, and
cost fields. It also correctly explains that the final reproducibility run
used cached evidence rather than claiming zero total inference cost.

## 5. Archive review

`code.zip` contains the expected implementation and release-support surfaces:

- application modules under `code/buy_or_wait/`;
- evaluation modules under `code/evaluation/`;
- production entry point `code/production/main.py`;
- test suite;
- scripts;
- root README;
- `evaluation/usage_report.md`.

The archive does not contain `output.csv`, which is correct because the
submission contract treats `output.csv` as a separate upload. It also does not
contain `log.txt`, which is correct because the transcript is a separate
submission artifact. No obvious secrets, `.env` files, private cache files,
artifacts, or bytecode were found in the archive listing.

## 6. Remaining cautions

### C-01 — Preserve exact artifact alignment

Do not regenerate `output.csv`, alter the usage report, or rebuild the zip
after this review without repeating the hash and schema checks. The usage
report explicitly refers to the cached run that produced the final output.

### C-02 — Upload transcript separately

The repository log exists and is gitignored. Upload it as the required
`chat_transcript` according to the HackerRank interface; do not expect it to be
inside `code.zip`.

### C-03 — Keep correctness claims precise

The full run establishes complete generation and structural validation. It
does not establish exact hidden-label accuracy. The solved-sample benchmark
has one fully matching structured row out of 25 and safe-amount exact accuracy
of 1/25. This is a quality limitation, not a packaging failure.

### C-04 — Verify the HackerRank upload UI

After uploading, confirm that the platform accepted:

1. `code.zip`;
2. root `output.csv`;
3. `log.txt` as the chat transcript;
4. any required contest metadata or declaration.

## 7. Final checklist

- [x] Full run completed for all 250 requests.
- [x] Root `output.csv` contains exactly 250 rows.
- [x] IDs are unique and match the evaluation request set.
- [x] Required header is exact.
- [x] Strict production read-back passed.
- [x] `code.zip` exists and includes `evaluation/usage_report.md`.
- [x] Usage report is nonempty and covers required metrics.
- [x] Zip contents were inspected.
- [x] No obvious secrets are in the zip.
- [x] `log.txt` exists as the separate transcript source.
- [ ] Upload the three submission artifacts and confirm platform acceptance.

## 8. Final recommendation

The repository is ready for submission. Submit the exact reviewed versions of
`code.zip`, `output.csv`, and `log.txt`. Keep the three files together as one
release set, and do not make further tuning changes unless you are prepared to
rerun the full generation, usage accounting, packaging, and hash checks.
