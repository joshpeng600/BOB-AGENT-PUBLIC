# exp_001 formal artifact-contract readiness — B

STATUS=READY_FOR_A_AND_E_ARTIFACT_CONTRACT_REREVIEW
ROLE=B
BRANCH=B-Part
ORIGIN_MAIN_SHA=b7001f693bb412a68398fb2ac47c6c40efe76ca0
IMPLEMENTATION_COMMIT_SHA=b99cba67224781652079793ba00bac5921593393
WORKTREE_CLEAN_AT_VERIFICATION=true
EXPERIMENT_ID=exp_001
E_BLOCKER_SOURCE=coordination/inbox/E/exp_001_pre_evaluation_readiness.md
EXPECTED_ARTIFACT_CONTRACT=PASS
ARTIFACT_BYTES_VERIFIED=true
REQUIRED_ARTIFACT_COUNT=5
EXACT_ARTIFACT_PATH_SET=true
EXECUTED_CONFIG_BINDING=true
FOCUSED_SYNTHETIC_TESTS=PASS_34_OF_34_1_PLATFORM_SKIP
PYTEST=NOT_RUN_FOR_FOLLOWUP_NOT_REQUIRED_BY_AGENTS_MD
UNIT_TESTS=PASS_88_OF_88_1_PLATFORM_SKIP
PROTECTED_HASHES=PASS
REPOSITORY_CONTRACTS=PASS
PREDICTION_CONTRACT=PASS
REAL_DATA_TRAINING_PERFORMED=false
FORMAL_VALID_METRICS_PRODUCED=false
TEST_ACCESS=false
REAL_VALID_RUN_ALLOWED=false
BLOCKERS=A and E must review this follow-up before changing REAL_VALID_RUN_ALLOWED
NEXT_RECEIVER=A_AND_E

## Scope

This follow-up is based on merged `main`
`b7001f693bb412a68398fb2ac47c6c40efe76ca0`. It is a setup contract correction
only and does not authorize or record a real baseline/BPR run, formal validation
metrics, or test access. B did not modify metric logic or any protected
`starter/` file.

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
- completed manifests reject both missing and unexpected artifacts, so the
  inventory is exactly the five non-self formal outputs;
- duplicate, absolute, non-normalized, and parent-traversal artifact paths are
  rejected consistently for both POSIX and Windows path syntax;
- `validate_artifact_files()` resolves declared files below the run directory,
  rejects symlinks and path escape, requires each path to be an ordinary file,
  recomputes SHA-256 from file bytes, and rejects any mismatch;
- `prediction_hash` and `checkpoint_hash` must equal their corresponding
  artifact-inventory hashes, which in turn must equal the actual file bytes;
- `resolved_config.json` must parse to the same object as `manifest.config`,
  and its canonical object hash must equal `manifest.config_hash`; canonical
  comparison distinguishes JSON values such as `1` and `1.0`;
- `tools/audit_run.py` invokes the complete artifact verifier relative to the
  directory containing `run_manifest.json`, so E cannot accept a manifest-only
  claim without the immutable files;
- the artifact verifier accepts only `status=completed`, so failed or stopped
  manifests cannot fall through as formal evidence;
- the `tools/validate_contract.py --type run-manifest --path <manifest>` CLI
  verifies completed artifact bytes relative to the manifest directory by
  default, with an explicit `--artifact-root` override when required;
- the runner invokes byte verification before it can retain a successful
  manifest;
- after training, the runner canonically compares the configuration returned by
  `execute()` with the configuration bound during preflight. A config/spec
  change between the two reads fails closed rather than producing a completed
  manifest for a different executed configuration;
- any late artifact-validation exception resets the manifest to
  `status=failed` and `exit_code=1`.

## Changed implementation

- `tools/run_experiment.py`
- `tools/validate_contract.py`
- `tools/audit_run.py`
- `contracts/run_manifest.template.json`
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
b99cba67224781652079793ba00bac5921593393
```

Results:

```text
python -m unittest tests.test_run_experiment tests.test_protected_and_contracts tests.test_audit -v
PASS: 34/34, 1 Windows privilege skip

python -m unittest discover -s tests -v
PASS: 88/88, 1 Windows privilege skip

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
executed-config drift rejection, tamper rejection,
missing/extra/duplicate/traversal/symlink rejection, and fail-closed manifest
status. The symlink regression is present and executes on platforms
that permit unprivileged symlink creation; this Windows account denied creation
with WinError 1314. Synthetic outputs are not formal evaluation input.

E should re-review only the artifact-package blocker after this implementation
is merged. The two human governance decisions in `coordination/current_state.json`
remain outside B's authority and must stay blocking until recorded by A.
