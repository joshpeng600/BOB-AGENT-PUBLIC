# exp_001 final setup integration readiness — A

STATUS=READY_FOR_PR_MERGE_THEN_E_INDEPENDENT_REREVIEW
ROLE=A
BRANCH=integration/exp-001-setup-final
BASE_MAIN_SHA=7dfeb682879aac5ecbcf8f3f84a065e5f54d17b2
IMPLEMENTATION_COMMIT_SHA=84d725ba9de831dfbeea9e9ed46b8173e540efdb
SOURCE_PR_32_HEAD_SHA=eec4893905d9efbaa634aadc10823c2037079322
EXPERIMENT_ID=exp_001
REAL_VALID_RUN_ALLOWED=false
REAL_DATA_TRAINING_PERFORMED=false
FORMAL_METRICS_PRODUCED=false
TEST_ACCESS=false

## Integrated setup-only changes

- Approved-run evidence is bound to the A-authored spec, spec approval ancestry,
  baseline approval ancestry, approved baseline/candidate route, objective, seed,
  valid-only mode, raw config bytes, and resolved config.
- A completed formal run must record the exact approved `training.max_batches`.
  A null approved value cannot be replaced by a CLI truncation.
- An explicitly bounded `--synthetic-smoke` path remains available, but it is
  marked `status=synthetic_smoke` and `evidence_tier=synthetic_only`; the formal
  auditor rejects it.
- Evaluation evidence is written to an exclusive same-directory temporary file,
  flushed and fsynced, published with a no-overwrite hard link, and verified after
  publication against the output hash, immutable prediction binding, directory
  binding, and clean Git commit.
- Existing output paths and symlinked output-directory components are rejected.
  Failures after publication remove only the exact inode created by the current
  invocation.

## Clean implementation verification

```text
python -m pytest -q
117 passed, 4 skipped, 39 subtests passed

python -m unittest discover -s tests -v
121 tests passed, 4 skipped

python scripts/check_repository_contracts.py
PASS: 27 JSON files plus JSONL/TOML

python scripts/check_protected_files.py
PASS: all seven protected starter files

python scripts/check_prediction_contract.py
PASS: 9 of 9 tests

python tools/verify_protected_files.py --manifest protected_manifest.json --repo-root .
PROTECTED_FILES=PASS

git diff --check origin/main...HEAD
PASS

git diff --name-only origin/main...HEAD -- starter
PASS: no output
```

## Authority and remaining gate

The exact setup-only cross-role integration authority is the active
`governance/manual_interventions.jsonl` record timestamped
`2026-08-30T13:47:13Z`. Its application is recorded separately; it grants no
standing permission, no scientific change, no real run, no metric production,
and no test access.

This readiness record is not an evaluation and does not open the real-valid
gate. After the PR merges with all four required checks passing, E must
independently rereview the resulting clean `main`. A may update
`REAL_VALID_RUN_ALLOWED` only after a separate E PASS record.
