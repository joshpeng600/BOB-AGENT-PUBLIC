# exp_001 fresh formal package handoff — B to E

STATUS=FORMAL_PACKAGES_READY_FOR_E
ROLE=B
EXPERIMENT_ID=exp_001
COMMIT_SHA=44fd36aa9b35b7fc9c01389e6dd453e972f16635
WORKTREE_CLEAN=true
DATA_HASH=69e5a6f656356832f7e1fa6a9774bc404030f32874e18e57e0f38b6a309a1002
SEED=0
MODE=valid-only
FULL_TRAINING_BUDGET=true
FORMAL_MAX_BATCHES=null
BASELINE_RUN_ID=run-20260830T173747251968Z-exp_001-44fd36aa
CANDIDATE_RUN_ID=run-20260830T173832514735Z-exp_001-44fd36aa
BASELINE_MANIFEST_SHA256=4532d1d2cd6c446e1871ac60c25c2f2a3559d65a95886ac038c9659386a64d38
CANDIDATE_MANIFEST_SHA256=da563985885f3e87b6a4c29730f6b7bbcfffb40785fbd5c2530cbad459123d42
BASELINE_PREDICTION_HASH=56d317930cd4bacb0fae0f6c6798834a440bc2a6c5a991a50c1ce81f406b86dc
CANDIDATE_PREDICTION_HASH=d137ce7d482d2cb8a2042d59831fa1fd1b1de50abd93bef288c189e11e05c0e3
BASELINE_CHECKPOINT_HASH=3ef70cf9f9fe7af74d6458ef25aff46002ed6fe0b9695e399805d8cd19110b32
CANDIDATE_CHECKPOINT_HASH=ab33916c2ce9fec82a6d35085f2ecd858b0add53eddde11ce62150c04c86d528
BASELINE_CONTRACT=PASS
CANDIDATE_CONTRACT=PASS
BASELINE_PREDICTION_CONTRACT=PASS_124909_ROWS
CANDIDATE_PREDICTION_CONTRACT=PASS_124909_ROWS
BASELINE_AUDIT=PASS
CANDIDATE_AUDIT=PASS
B_TRAINING_PR25_EVIDENCE_USED=false
PREDICTIONS_MODIFIED=false
test_access=false
NEXT_RECEIVER=E

## Frozen package paths

- Baseline: `artifacts/exp_001_formal_44fd36_baseline`
- Candidate: `artifacts/exp_001_formal_44fd36_candidate`

Each local Git-ignored directory contains exactly the required formal package:
`run_manifest.json`, `valid_predictions.csv`, `checkpoint.npz`,
`resolved_config.json`, `training_history.json`, and `runner_metrics.json`.
Large artifacts and development data are not committed to Git.

Both runs were produced after PR #38 activated exactly one fresh formal pair.
They use the same clean commit, development-data hash, unchanged FM feature
set, seed 0, and full approved budget. Neither command included
`--max-batches`, `--synthetic-smoke`, or any test operation.

## Verification performed by B

- Real-data preflight passed for both approved routes with 1,266,021 rows,
  maximum date 20220428, binary labels, and zero test rows.
- `tools/validate_contract.py --type run-manifest` passed with file-byte
  verification for both package roots.
- `tools/validate_predictions.py --split valid` passed for both predictions at
  exactly 124,909 rows.
- `python -m tools.audit_run` passed commit, clean-state, data-boundary, hash,
  artifact, and command checks for both manifests.

## Process incident disclosure

After both fresh B runs had completed and their immutable hashes were fixed,
the coordinating root session accidentally opened the quarantined PR #25
metrics while looking for an output schema. Those old metrics were not read
before or during training, were not used to configure either run, and did not
modify either prediction or checkpoint. To prevent evaluator contamination,
that coordinating session did not perform the E score. A new isolated E agent
with no inherited conversation context was explicitly prohibited from reading
PR #25 and was assigned the fresh packages. A must retain this disclosure when
deciding whether the contained, non-causal process incident is acceptable.
