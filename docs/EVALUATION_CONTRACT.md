# E evaluation and evidence contract

## Evaluation interface

Only the protected `starter/evaluate.py` defines GAUC, nDCG@5, and primary.
Normal development evaluates `valid` only:

```bash
python3 -m tools.safe_evaluate \
  --prediction path/to/valid_predictions.csv \
  --split valid \
  --data-dir path/to/KuaiRand-Pure/data \
  --output reports/metrics.json
```

The gate writes GAUC, nDCG@5, primary, rows, users, evaluator hash,
prediction hash, runtime `commit_sha`, `evaluator_role=E`, and worktree state. It rejects the run before calling
the official evaluator if any contract fails.

## Rejection conditions

- Protected file is missing or its SHA-256 differs from
  `protected_manifest.json`.
- Prediction header is not exactly `row_id,user_id,video_id,score`.
- Prediction is shorter or longer than the selected split.
- `row_id` is not zero-based and continuous.
- `user_id` or `video_id` differs from the same official-data row.
- A score is non-numeric, NaN, or infinite.
- Evaluator arrays differ in length, contain a non-binary label, or have an
  empty user ID.
- A test operation lacks a valid final human approval.

## Protected hashes

The authoritative values live in `protected_manifest.json`. Do not update the
manifest to conceal an accidental edit. Restore the official Starter Kit file
instead.

Protected text is checked with CRLF normalized to LF, so a Windows checkout
does not fail solely because of line endings. `.gitattributes` also requests LF
for source and evidence files. All non-line-ending byte changes remain covered
by SHA-256 and are rejected.

## Prediction contract for B

B owns training and valid-only execution. Its run manifest uses
`executor_role=B` and the clean runtime `commit_sha`. B provides one immutable
CSV with exactly four columns:

```text
row_id,user_id,video_id,score
```

One row must correspond to one official split row. Preserve official order.
Repeated `(user_id, video_id)` pairs are valid; `row_id` is the unique alignment
key. Scores may be any finite real values because only relative ranking matters.

## Metrics contract for A and E

Each iteration copies `contracts/metrics.template.json`. A freezes the hypothesis,
baseline experiment, approval baseline (`approved_against_commit_sha`), and strict
success rule `candidate_primary - baseline_primary > 0.002` before execution. E independently records the
actual code diff, validation metrics, errors, recovery, manual interventions,
tokens, wall-clock time, iterations, GPU hours, full `commit_sha`,
`worktree_clean`, config, data hash, seed, and protected hashes after B produces
immutable predictions.

An A-approved experiment starts through the spec, never a filename-derived ID:

```bash
python tools/run_experiment.py \
  --experiment-spec experiments/exp_001.json \
  --config configs/candidates/bpr_fm.json \
  ...
```

`experiment_id` comes only from an `APPROVED_FOR_IMPLEMENTATION` spec whose
`implementation_config` matches the supplied config. Smoke runs use explicitly
synthetic fixtures and do not establish metric conclusions. Missing dependencies
stop with failed evidence; the runner must not install them automatically.

## Independent audit

Copy `contracts/run_manifest.template.json`, fill it, and run:

```bash
python3 -m tools.audit_run --manifest path/to/run_manifest.json
```

The audit accepts only a full `commit_sha` matching the current commit,
`worktree_clean=true`, a
clean actual worktree, complete config/data/seed/hash evidence, development data
ending no later than 2022-04-28, matching protected hashes, and no test-scoring
command in the recorded command history.

## Final approval

The human approver creates a copy of `contracts/final_approval.template.json`
outside the repository after the final commit is frozen. The approval checker
will reject placeholders, shortened SHAs, dirty worktrees, and changed hashes:

```bash
python3 -m tools.final_approval --approval path/to/final_approval.json
```

Approval never permits local hidden-test scoring. The organizer provides an
identity-only file with the exact header `row_id,user_id,video_id`; label
columns are rejected. Freeze one final submission without evaluating it:

```bash
python3 -m tools.final_submission \
  --approval path/to/final_approval.json \
  --candidate artifacts/final/candidate.csv \
  --identities path/to/hidden_test_identities.csv \
  --output artifacts/final/submission.csv \
  --manifest artifacts/final/submission_manifest.json
```

The manifest binds submission and identity SHA-256 values. Scoring occurs only
on the organizer side.
