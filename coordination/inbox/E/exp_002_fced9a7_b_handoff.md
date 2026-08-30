# exp_002 formal package handoff — B to E

STATUS=FORMAL_PACKAGES_READY_FOR_E
ROLE=B
PHASE=PACKAGE_AUDIT
EXPERIMENT_ID=exp_002
COMMIT_SHA=fced9a79ae3e06af69e06d319ee316e77fcce98a
WORKTREE_CLEAN=true
EXPERIMENT_SPEC_HASH=c3d1257751d2abf15d62a0638679efe892cc13a8ff3325630ab2acbbece5c8c9
BASELINE_CONFIG_INPUT_HASH=5221e0efdaace6f0aaa196da3cfdf51a4fdb154cf3043cd6b71252a62cf0823c
CANDIDATE_CONFIG_INPUT_HASH=4ae653c2a68c1dc461ff2149540920e009355637e22e557b70c68e41460d2b61
BASELINE_RESOLVED_CONFIG_HASH=6ba29a9cd553ccdaf6624ac7835a8143603329504b03b6c2f40d376f35988ed8
CANDIDATE_RESOLVED_CONFIG_HASH=5ee103e57bdf6b1679a21f671869f937e76e6f4b5439bb2f0db271b5b20e3a3f
DATA_HASH=69e5a6f656356832f7e1fa6a9774bc404030f32874e18e57e0f38b6a309a1002
MAX_DATE=20220428
TEST_ROWS=0
SEED=0
MODE=valid-only
FULL_TRAINING_BUDGET=true
FORMAL_MAX_BATCHES=null
SMOKE_STATUS=PASS_SETUP_EVIDENCE_PR_47
BASELINE_STATUS=COMPLETED_AND_AUDITED
CANDIDATE_STATUS=COMPLETED_AND_AUDITED
BASELINE_RUN_ID=run-20260830T204322000532Z-exp_002-fced9a79
CANDIDATE_RUN_ID=run-20260830T204431345558Z-exp_002-fced9a79
BASELINE_BATCHES_SEEN=470
CANDIDATE_BATCHES_SEEN=658
BASELINE_MANIFEST_SHA256=2035917580b635ee6f7888095a84b098c79ab33aa3b0717e84383f540bee2031
CANDIDATE_MANIFEST_SHA256=08e651b19777e2332dcad73155b09b6a2900657ce9a396294d951238814ddb61
BASELINE_PREDICTION_HASH=5bd21e55d1720efa77f9b4c5c76c9cfd0bbc816a29cd0dcd65e2e13ad4de587b
CANDIDATE_PREDICTION_HASH=4b4105631ffff4543f7e66965138b8ecd2bd44151da9ccac90d4282ea616ed9e
BASELINE_CHECKPOINT_HASH=a8c232704c417c8493bce12fc7f27a31431eabfc85d08fc076669df528b63f85
CANDIDATE_CHECKPOINT_HASH=1f0934e5e758896ac595c8e8ae26791b0a36dd479c6fc4fdc6a70d9b61aeb997
BASELINE_CONTRACT=PASS
CANDIDATE_CONTRACT=PASS
BASELINE_PREDICTION_CONTRACT=PASS_124909_ROWS
CANDIDATE_PREDICTION_CONTRACT=PASS_124909_ROWS
BASELINE_AUDIT=PASS
CANDIDATE_AUDIT=PASS
COMMAND_EXIT_CODES=BASELINE_0,CANDIDATE_0,CONTRACTS_0,PREDICTIONS_0,AUDITS_0
RETRY_COUNT=0
PR25_EVIDENCE_USED=false
PREDICTIONS_MODIFIED=false
OFFICIAL_E_EVALUATION_PERFORMED=false
OFFICIAL_E_METRICS_PRODUCED=false
FORMAL_METRICS_PRODUCED=false
test_access=false
NEXT_RECEIVER=E

## Frozen package paths

- Baseline: `artifacts/exp002_fced9a7_baseline`
- Candidate: `artifacts/exp002_fced9a7_candidate`
- Local baseline absolute path: `C:\Users\asus-pc\Desktop\BOBAAA\BOB-AGENT\.worktrees\b-exp002-formal-fced9a7\artifacts\exp002_fced9a7_baseline`
- Local candidate absolute path: `C:\Users\asus-pc\Desktop\BOBAAA\BOB-AGENT\.worktrees\b-exp002-formal-fced9a7\artifacts\exp002_fced9a7_candidate`

Each Git-ignored directory contains `run_manifest.json`,
`valid_predictions.csv`, `checkpoint.npz`, `resolved_config.json`,
`training_history.json`, and `runner_metrics.json`. Data, predictions,
checkpoints, and generated artifacts are not committed to Git.

Both runs were produced after PR #49 activated exactly one fresh exp_002
formal pair. They use the same clean commit, data hash, feature set, seed, and
full approved budget. Neither command included `--max-batches`,
`--synthetic-smoke`, or any test operation.

## Artifact SHA-256 inventory

Baseline:

- `valid_predictions.csv`: `5bd21e55d1720efa77f9b4c5c76c9cfd0bbc816a29cd0dcd65e2e13ad4de587b`
- `checkpoint.npz`: `a8c232704c417c8493bce12fc7f27a31431eabfc85d08fc076669df528b63f85`
- `resolved_config.json`: `267a3b9ff1db3144d1d0e620513f917d84c5ef0a8eb8cec34365696e81315a8f`
- `training_history.json`: `c01077bbc8d5e023650e495450b7b6ff55dd38f7e09b2d90a7ba0e1051869818`
- `runner_metrics.json`: `0684a6ef0530a0546e2ffc3896afffe0e511cb67ce172b2b7551b4a53923d60c`

Candidate:

- `valid_predictions.csv`: `4b4105631ffff4543f7e66965138b8ecd2bd44151da9ccac90d4282ea616ed9e`
- `checkpoint.npz`: `1f0934e5e758896ac595c8e8ae26791b0a36dd479c6fc4fdc6a70d9b61aeb997`
- `resolved_config.json`: `3ff271f2eacf018355f4bb0a232a7af4cae2cb17a148db6f177ca9865a744c83`
- `training_history.json`: `842604e41de8fe2ca58ca376336c2b8ec5c7f22e4895451b9d0afd4df5e3588f`
- `runner_metrics.json`: `a540f345e3d18ece1afd90423cb367f12506a8c4ea137e34dd8e356d4fdf948d`

## B verification

- Real-data preflight passed for both approved routes with 1,266,021 rows,
  maximum date 20220428, binary labels, and zero test rows.
- pytest passed 121 tests with 4 platform skips; unittest passed 125 tests
  with 4 platform skips.
- Repository contracts, protected files 7/7, and prediction contract 9/9
  passed before the formal pair.
- `tools/validate_contract.py --type run-manifest` passed with artifact-byte
  verification for both package roots.
- `tools/validate_predictions.py --split valid` passed both immutable
  predictions at exactly 124,909 rows.
- `python -m tools.audit_run` passed commit, clean-state, data-boundary, hash,
  artifact, route, and command checks for both manifests.

The runner generated its required `runner_metrics.json` and emitted an
internal validation summary. B did not use that summary for comparison,
selection, or decision-making and does not report metric values here. E must
independently evaluate the immutable prediction bytes through the approved
valid-only evaluation route.
