# exp_001 formal artifact-contract readiness — B

STATUS=READY_FOR_E_ARTIFACT_CONTRACT_REREVIEW
ROLE=B
BRANCH=B-Part
ORIGIN_MAIN_SHA=4170b2e1377be89205fbe9c93cbafafa81c7e4c0
IMPLEMENTATION_COMMIT_SHA=24235daf9a0a5e6d4272aa16270befd9cb18bb2b
WORKTREE_CLEAN_AT_VERIFICATION=true
EXPERIMENT_ID=exp_001
E_BLOCKER_SOURCE=coordination/inbox/E/exp_001_pre_evaluation_readiness.md
EXPECTED_ARTIFACT_CONTRACT=PASS
ARTIFACT_BYTES_VERIFIED=true
REQUIRED_ARTIFACT_COUNT=5
PYTEST=PASS_84_TESTS_26_SUBTESTS_1_PLATFORM_SKIP
UNIT_TESTS=PASS_85_OF_85_1_PLATFORM_SKIP
PROTECTED_HASHES=PASS
REPOSITORY_CONTRACTS=PASS
PREDICTION_CONTRACT=PASS
REAL_DATA_TRAINING_PERFORMED=false
FORMAL_VALID_METRICS_PRODUCED=false
TEST_ACCESS=false
REAL_VALID_RUN_ALLOWED=false
BLOCKERS=human governance decisions recorded in coordination/current_state.json remain pending; this B change closes only E's artifact-contract blocker
NEXT_RECEIVER=E

## Scope

This is a setup contract correction only. It does not authorize or record a
real baseline/BPR run, formal validation metrics, or test access. B did not
modify E-owned audit/evaluation logic or any protected `starter/` file.

## E blocker resolution

The completed run-manifest contract now requires these five immutable artifacts:

```text
valid_predictions.csv
checkpoint.npz
resolved_config.json
training_history.json
runner_metrics.json
```

The run manifest itself is the signed inventory container and is not included
in its own artifact list, avoiding a self-referential hash. `run.log` and
`exit_status.json` remain operational evidence rather than completed scientific
artifacts.

The complete correction provides all of the following:

- the runner records a raw SHA-256 entry for `resolved_config.json`;
- completed manifests reject a missing required artifact;
- duplicate, absolute, non-normalized, and parent-traversal artifact paths are
  rejected;
- `validate_artifact_files()` resolves declared files below the run directory,
  rejects symlinks and path escape, requires each path to be an ordinary file,
  recomputes SHA-256 from file bytes, and rejects any mismatch;
- `prediction_hash` and `checkpoint_hash` must equal their corresponding
  artifact-inventory hashes, which in turn must equal the actual file bytes;
- `resolved_config.json` must parse to the same object as `manifest.config`,
  and its canonical object hash must equal `manifest.config_hash`;
- `tools/audit_run.py` invokes the complete artifact verifier relative to the
  directory containing `run_manifest.json`, so E cannot accept a manifest-only
  claim without the immutable files;
- the `tools/validate_contract.py --type run-manifest --path <manifest>` CLI
  verifies completed artifact bytes relative to the manifest directory by
  default, with an explicit `--artifact-root` override when required;
- the runner invokes byte verification before it can retain a successful
  manifest;
- any late artifact-validation exception resets the manifest to
  `status=failed` and `exit_code=1`.

## Changed implementation

- `tools/run_experiment.py`
- `tools/validate_contract.py`
- `tools/audit_run.py`
- `tests/test_run_experiment.py`
- `tests/test_protected_and_contracts.py`
- `tests/test_audit.py`

No C data implementation, D scientific logic, E metric implementation,
governance state, approved config, experiment specification, or protected file
was modified. A's latest handoff explicitly included `tools/audit_run.py` in
B's authorized implementation scope.

## Verification on clean implementation commit

Implementation commit:

```text
24235daf9a0a5e6d4272aa16270befd9cb18bb2b
```

Results:

```text
python -m pytest -q
PASS: 84 tests, 26 subtests, 1 Windows privilege skip

python -m unittest discover -s tests -v
PASS: 85/85, 1 Windows privilege skip

python scripts/check_repository_contracts.py
PASS: 22 JSON files plus JSONL/TOML

python scripts/check_protected_files.py
PASS: all seven protected starter files

python scripts/check_prediction_contract.py
PASS: 9/9

git diff --check
PASS

git diff -- starter/
PASS: no diff
```

Synthetic regression coverage verifies the complete inventory, audit entry
point, file-byte and cross-hash matching, resolved-config semantic binding,
tamper rejection, missing/duplicate/traversal/symlink rejection, and fail-closed
manifest status. The symlink regression is present and executes on platforms
that permit unprivileged symlink creation; this Windows account denied creation
with WinError 1314. Synthetic outputs are not formal evaluation input.

E should re-review only the artifact-package blocker after this implementation
is merged. The two human governance decisions in `coordination/current_state.json`
remain outside B's authority and must stay blocking until recorded by A.
