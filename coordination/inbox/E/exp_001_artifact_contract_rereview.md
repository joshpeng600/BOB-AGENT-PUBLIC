# exp_001 complete artifact-contract independent rereview — E

STATUS=PASS
ROLE=E
REVIEW_TYPE=SETUP_ONLY
REVIEWED_MAIN_SHA=bb327fb41c483dec03a056a12100e3229e7fddf0
REVIEWED_PR_20_MERGE_SHA=1ae9a35d9324948ca6cac5af2f7b56cf588dcd2c
REVIEWED_PR_21_MERGE_SHA=b7001f693bb412a68398fb2ac47c6c40efe76ca0
REVIEWED_PR_22_MERGE_SHA=cb61b52affd5ecdb4095312087400fb482d8301b
EXPECTED_ARTIFACT_CONTRACT=PASS
PROTECTED_HASHES=PASS
REPOSITORY_CONTRACTS=PASS
PREDICTION_CONTRACT=PASS
FORMAL_EVALUATION_PERFORMED=false
FORMAL_METRICS_PRODUCED=false
REAL_DATA_ACCESSED=false
TRAINING_PERFORMED=false
TEST_ACCESS=false
NEXT_RECEIVER=A

## Independent conclusion

E independently reviewed the complete artifact contract merged through PR #22
against the immutable `origin/main` commit above. The setup contract is ready
for A's gate decision. This conclusion validates interfaces and fail-closed
behavior only; it is not validation metric evidence and does not itself set
`REAL_VALID_RUN_ALLOWED=ALLOWED`.

The completed-run path now provides the required protections:

- completed manifests require exactly these five formal artifacts:
  `valid_predictions.csv`, `checkpoint.npz`, `resolved_config.json`,
  `training_history.json`, and `runner_metrics.json`;
- every artifact path must be unique, normalized, repository-platform-safe,
  relative to the run directory, non-symlink, and an ordinary file;
- `tools/audit_run.py` resolves artifacts from the directory containing
  `run_manifest.json` and `tools/validate_contract.py` hashes bytes through
  fixed, no-follow file handles while retaining and rechecking path bindings;
- artifact bytes are hashed repeatedly and rechecked after semantic validation;
- `resolved_config.json` is parsed from the captured bytes, must equal
  `run_manifest.config`, and its canonical object hash must equal `config_hash`;
- `prediction_hash` and `checkpoint_hash` must equal both their artifact-entry
  hashes and the bytes observed by the auditor;
- `experiment_spec_path` is a normalized repository-relative non-escaping
  path and `experiment_spec_hash` must equal the current repository file bytes;
- the runner parses approved spec/config bytes once, binds execution to those
  objects, and rejects raw spec/config drift before completion;
- all declared development-data sources are hash-checked, then the consumed
  sources are copied from no-follow handles into a private execution snapshot;
  the original input snapshot and source hashes are checked again after use;
- the runner validates the executed resolved configuration and clean Git state
  before constructing a completed candidate manifest;
- artifact validation failure, `KeyboardInterrupt`, `SystemExit`, and other
  `BaseException` paths persist `status=failed` with nonzero exit status;
- failed or stopped manifests cannot be accepted as completed evidence;
- ordinary run specifications and recorded commands remain valid-only and deny
  test access. No test data was accessed in this rereview.

## Commands and results

All local commands ran on a clean worktree containing the reviewed main tree.
They used only repository code and temporary synthetic fixtures; `data/dev` was
not read.

```text
python -m unittest tests.test_audit tests.test_protected_and_contracts tests.test_run_experiment -v
PASS: 46 tests, 1 Windows privilege skip (45 executed and passed)

python scripts/check_protected_files.py
PASS: all seven protected starter files

python scripts/check_repository_contracts.py
PASS: 23 JSON files plus JSONL/TOML

python scripts/check_prediction_contract.py
PASS: 9/9 tests

python -m unittest discover -s tests -v
PASS: 100 tests, 1 Windows privilege skip (99 executed and passed)

python -m pytest -q
PASS: 99 passed, 1 Windows privilege skip, 30 subtests passed

git diff --check
PASS

git diff -- starter/
PASS: no diff
```

The skipped local test is the artifact-symlink regression because this Windows
account lacks symlink-creation privilege (WinError 1314). It is not an untested
contract: PR #22's Linux GitHub Actions unit-test job ran the same suite with
`100 passed, 30 subtests passed` and no skip. Source inspection also confirms
explicit `lstat`, regular-file, identity, and `O_NOFOLLOW` checks.

## GitHub evidence reviewed

- PR #20: merged; all four required checks passed.
- PR #21: merged; all four required checks passed.
- PR #22: merged; all four required checks passed.
- PR #24: the repository owner's exact PR #22 ownership exception is recorded;
  all four required checks passed.

## Governance anomaly outside this review PR

At review time, GitHub PR #25 from the pre-existing `E-Part` history was open
and contained formal validation metrics created while main still recorded
`REAL_VALID_RUN_ALLOWED` as blocked. E did not inspect or rely on its ignored
run artifacts or development data, and this setup rereview intentionally starts
from `origin/main` so none of PR #25's metric files are included here.

PR #25 is not eligible for automatic merge under the recorded gate merely
because CI passes. A must close or otherwise formally reconcile it; its metrics
must not be treated as approved cycle evidence. A may consider opening the real
valid gate only from this setup rereview and the existing C/D/B setup evidence,
after keeping PR #25 outside main.
