# exp_001 freeze readiness — B

STATUS=BLOCKED
ROLE=B
BRANCH=B-Part
ORIGIN_MAIN_SHA=4d26e44f39dd6f9d1c42462411c19a2ddfbe49d3
IMPLEMENTATION_COMMIT_SHA=5ab859b135be02db07d03a24a1827a81ecac656d
HEAD_SHA=NOT_EMBEDDED_TO_AVOID_GIT_SELF_REFERENCE
WORKTREE_CLEAN=true
EXPERIMENT_ID=exp_001
EXPERIMENT_SPEC=experiments/exp_001.json
BASELINE_CONFIG=configs/approved/baseline_fm.json
CANDIDATE_CONFIG=configs/candidates/bpr_fm.json
DATA_MANIFEST_SHA256=69e5a6f656356832f7e1fa6a9774bc404030f32874e18e57e0f38b6a309a1002
C_DATA_EVIDENCE_REVIEWED=true
MAX_DATE=20220428
TEST_ROWS=0
PAIR_FEASIBILITY_REVIEWED=true
E_CROSS_ROLE_CHANGES_REVIEWED=true
B_ACCEPTS_E_VALIDATOR_TEST_CHANGES=true
D_INTERFACE_VERIFIED=true
SYNTHETIC_SMOKE=PASS
REAL_DATA_TRAINING_PERFORMED=false
FORMAL_VALID_METRICS_PRODUCED=false
TEST_ACCESS=false
PROTECTED_HASHES=PASS
REPOSITORY_CONTRACTS=PASS
PREDICTION_CONTRACT=PASS
UNIT_TESTS=PASS_77_OF_77
PYTEST=BLOCKED_MODULE_NOT_INSTALLED
BLOCKERS=python -m pytest -q failed because the active Python runtime has no pytest module; policy forbids automatic dependency installation
NEXT_RECEIVER=A

## Scope and freeze semantics

This is implementation and synthetic-fixture readiness evidence only. It does
not authorize or record a real baseline/BPR run, formal validation metrics, or
test access. The final branch HEAD is intentionally reported to A after this
file is committed, because embedding that commit SHA here would create a Git
self-reference.

The B-owned runner and validators required no code changes after synchronization
with `origin/main`. `IMPLEMENTATION_COMMIT_SHA` identifies B's runner
implementation commit. A must independently verify that the final B-Part HEAD
is a clean descendant of both that commit and the synchronized origin/main SHA.

## C development-data evidence

- Local `data/dev/dataset_manifest.json` SHA-256 matched
  `69e5a6f656356832f7e1fa6a9774bc404030f32874e18e57e0f38b6a309a1002`.
- Read-only preflight returned:

```text
ROWS=1266021
TEST_ROWS=0
MIN_DATE=20220409
MAX_DATE=20220428
LABEL_VALUES=[0, 1]
PREFLIGHT=PASS
```

- C's committed readiness evidence was reviewed: train-only same-user pair
  feasibility is verified with `PAIR_COUNT=382579`, `ELIGIBLE_USERS=24290`,
  `TOTAL_USERS=26210`, and `USER_COVERAGE=0.926745516978`.
- No real-data training function was invoked.

## Runner and D interface review

The runner accepts the approved experiment spec and either the matching
candidate config or its declared baseline config. It obtains `experiment_id`
only from an `APPROVED_FOR_IMPLEMENTATION` spec, validates canonical model and
training fields, routes pointwise BCE and same-user BPR separately, records
complete run evidence and hashes, refuses dirty/short-SHA/protected/test access,
does not install dependencies, and retries only an explicitly classified
transient infrastructure error at most once.

D's FactorizationMachine construction, pointwise path, same-user pair sampler,
BPR epoch path, pair coverage, checkpoint save/restore, and deterministic seed
interfaces were reviewed and passed 10 focused synthetic tests.

## E cross-role review

The B-owned changes introduced through PR #10 in
`tools/validate_predictions.py`, `tests/test_audit.py`,
`tests/test_predictions.py`, and `tests/test_safe_evaluate.py` were reviewed.
They preserve ordinary valid-only behavior; deny test before data access; reject
dirty state, short SHA, wrong role, missing or mismatched hashes, NaN/Inf, and
prediction order violations; and do not change the protected evaluator or make
E the owner of runner/training logic. B technically accepts these validator/test
changes. This acceptance is not an A/manual governance exception.

## Synthetic smoke

All smoke inputs were temporary synthetic fixtures. No synthetic result is a
formal metric claim and no synthetic prediction is intended for E evaluation.

- `python -m unittest tests.test_run_experiment -v` — PASS (5 tests), including
  repository-spec routing for synthetic pointwise baseline and BPR, canonical
  artifacts/manifests, fail-closed dirty state, and retry policy.
- `python -m unittest tests.test_predictions -v` — PASS (7 tests), including
  denial of a non-valid split before data access.
- D interface focused suite — PASS (10 tests).
- E cross-role audit/evaluation focused suite — PASS (18 tests).

## Repository verification

- `python -m unittest discover -s tests -v` — PASS (77 tests).
- `python scripts/check_repository_contracts.py` — PASS (21 JSON files plus
  JSONL/TOML validated).
- `python scripts/check_protected_files.py` — PASS (all seven starter hashes).
- `python scripts/check_prediction_contract.py` — PASS (9 tests).
- `git diff --check` — PASS.
- `git diff -- starter/` — PASS (no diff).
- `data/dev` remains ignored and no data, prediction, checkpoint, or generated
  artifact is staged.
- `python -m pytest -q` — BLOCKED: `No module named pytest` in the active
  `D:\Program Files\python.exe` runtime. No other installed Python/pytest
  runtime was found, and no dependency was installed automatically.

Until A resolves or explicitly accepts the missing-pytest verification blocker
and updates the real-validation gate, B must not run real baseline/BPR or create
formal valid predictions.
