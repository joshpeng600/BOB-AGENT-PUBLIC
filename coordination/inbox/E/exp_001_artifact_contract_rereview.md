# exp_001 complete artifact-contract independent rereview — E

STATUS=PASS
ROLE=E
REVIEW_TYPE=SETUP_ONLY
REVIEWED_MAIN_SHA=afe5b795abacb408c668f05db1a61b6a5af03879
REVIEWED_ARTIFACT_CODE_BASE_SHA=bb327fb41c483dec03a056a12100e3229e7fddf0
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
PR_25_EVIDENCE_ACCEPTED=false
REAL_VALID_GATE_RECOMMENDATION=BLOCKED_PENDING_A_RECONCILIATION
NEXT_RECEIVER=A

## Independent conclusion

E independently reviewed the complete artifact contract merged through PR #22
against the immutable `origin/main` commit above. PR #25 changed only E evidence
documents after the artifact-code review baseline; it did not alter the audited
implementation. The technical setup contract passes, but A must reconcile the
PR #25 gate incident described below before making any real-valid gate decision.
This conclusion validates interfaces and fail-closed behavior only; it is not
validation metric evidence and does not itself set
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
PASS: 25 JSON files plus JSONL/TOML

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
- PR #25: merged as `afe5b795abacb408c668f05db1a61b6a5af03879`;
  all four CI checks passed, but CI success did not authorize a formal valid run
  while the A-owned stage gate remained blocked.

## Governance anomaly outside this review PR

During this rereview, another integration actor merged GitHub PR #25 from the
pre-existing `E-Part` history. It contains formal validation metrics produced
while main still recorded `REAL_VALID_RUN_ALLOWED` as blocked. Passing CI does
not supersede that stage gate. E did not inspect or rely on PR #25's ignored run
artifacts or development data, and this setup rereview did not reproduce or
validate those metrics.

PR #25 is therefore not accepted as authoritative cycle evidence. A must record
and reconcile the incident, explicitly keep the PR #25 result out of experiment
selection, and decide whether its committed evidence should be reverted through
a normal PR. Until that A-owned reconciliation is merged, the real-valid gate
must remain blocked. A may then consider a fresh authorization based on this
technical setup PASS and the existing C/D/B setup evidence.
