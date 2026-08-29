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
prediction hash, commit, and worktree state. It rejects the run before calling
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

B provides one CSV with exactly four columns:

```text
row_id,user_id,video_id,score
```

One row must correspond to one official split row. Preserve official order.
Repeated `(user_id, video_id)` pairs are valid; `row_id` is the unique alignment
key. Scores may be any finite real values because only relative ranking matters.

## Metrics contract for A

Each iteration copies `contracts/metrics.template.json` and fills every field.
A records the hypothesis and baseline experiment before execution, then records the
actual code diff, metrics, errors, recovery, manual interventions, tokens,
wall-clock time, iterations, GPU hours, full `commit_sha`, `worktree_clean`, config,
data hash, seed, and protected hashes after execution.

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

No test command is documented here. Approval verification is deliberately a
separate manual release step.
