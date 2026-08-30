# exp_001 formal artifact-contract readiness — B

STATUS=READY_FOR_A_AND_E_ARTIFACT_CONTRACT_REREVIEW
ROLE=B
BRANCH=B-Part
ORIGIN_MAIN_SHA=b7001f693bb412a68398fb2ac47c6c40efe76ca0
IMPLEMENTATION_COMMIT_SHA=366951c06be3aedddca4f6da7f35e479ed374df4
WORKTREE_CLEAN_AT_VERIFICATION=true
EXPERIMENT_ID=exp_001
E_BLOCKER_SOURCE=coordination/inbox/E/exp_001_pre_evaluation_readiness.md
EXPECTED_ARTIFACT_CONTRACT=PASS
ARTIFACT_BYTES_VERIFIED=true
REQUIRED_ARTIFACT_COUNT=5
EXACT_ARTIFACT_PATH_SET=true
EXECUTED_CONFIG_BINDING=true
SPEC_AND_CONFIG_BYTES_FROZEN=true
DATA_MANIFEST_SOURCE_HASHES_VERIFIED=true
PRIVATE_EXECUTION_DATA_SNAPSHOT=true
BASEEXCEPTION_FAIL_CLOSED=true
FIXED_HANDLE_ARTIFACT_SNAPSHOT=true
EXPERIMENT_SPEC_HASH_AUDITED=true
FOCUSED_SYNTHETIC_TESTS=PASS_45_SKIP_1_OF_46
PYTEST=NOT_RUN_FOR_FOLLOWUP_NOT_REQUIRED_BY_AGENTS_MD
UNIT_TESTS=PASS_99_SKIP_1_OF_100
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
- formal runs accept only repository-owned specs below `experiments/` and
  configs below `configs/`, so a runner-completed package is also resolvable by
  the independent auditor;
- the exact approved spec/config bytes are parsed once, frozen into execution,
  and rehashed after execution. Changes to either raw input fail closed;
- when `dataset_manifest.json` exists, every declared source SHA-256 is checked
  against its actual file bytes. The three sources consumed by `starter.data`
  are then copied through fixed no-follow handles into a private verified
  execution snapshot, so temporary source replacement cannot influence the
  loader and then be hidden by restoration;
- the original manifest and all declared source hashes are checked again after
  execution, and the per-source hashes are recorded in `run_manifest.data`;
- artifact validation opens every formal output once through a no-follow file
  descriptor, keeps all handles open, hashes each handle repeatedly, parses
  `resolved_config.json` from the captured bytes rather than reopening its
  path, and rechecks both path identity and handle bytes at the end;
- `experiment_spec_hash` is mandatory for completed run manifests, and
  `tools/audit_run.py` compares it with the actual repository spec bytes;
- `status=completed` is constructed in a separate candidate manifest and is
  assigned only after artifact verification succeeds. `KeyboardInterrupt`,
  `SystemExit`, and other `BaseException` paths persist `status=failed` and a
  nonzero exit code before propagation;
- `tools/safe_evaluate.py` independently hashes the immutable prediction both
  before and after evaluator consumption and records that hash for E's
  cross-check against the audited manifest.

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
366951c06be3aedddca4f6da7f35e479ed374df4
```

Results:

```text
python -m unittest tests.test_run_experiment tests.test_protected_and_contracts tests.test_audit -v
PASS: 45 passed, 1 Windows privilege skip (46 total)

python -m unittest discover -s tests -v
PASS: 99 passed, 1 Windows privilege skip (100 total)

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

Synthetic regression coverage verifies the complete inventory, runner-to-audit
compatibility, file-byte and cross-hash matching, fixed-handle resolved-config
semantic binding, raw spec/config drift rejection, every declared dataset
source hash, persistent and restored CSV replacement, `KeyboardInterrupt`
fail-closed status, post-hash artifact replacement, and
missing/extra/duplicate/traversal/symlink rejection. The symlink regression is
present and executes on platforms
that permit unprivileged symlink creation; this Windows account denied creation
with WinError 1314. Synthetic outputs are not formal evaluation input.

No completed formal run evidence predates this contract correction. The
strengthened version-1 validator intentionally rejects any earlier incomplete
manifest that lacks `experiment_spec_hash` or the exact five-file inventory;
such a manifest was never acceptable formal evidence.

E should re-review only the artifact-package blocker after this implementation
is merged. The two human governance decisions in `coordination/current_state.json`
remain outside B's authority and must stay blocking until recorded by A.
