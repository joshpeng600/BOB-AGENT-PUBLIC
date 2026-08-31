# exp_003 formal package handoff — B to E

STATUS=FORMAL_PACKAGES_READY_FOR_E
ROLE=B
PHASE=PACKAGE_AUDIT
EXPERIMENT_ID=exp_003
COMMIT_SHA=420a5b1652cf3592c1074c8a3608be03806ea82a
WORKTREE_CLEAN=true
EXPERIMENT_SPEC_HASH=79c0e54f962c84213c0150474894ff695d5d6acfed85aa2955abb173b425f20c
BASELINE_CONFIG_INPUT_HASH=5221e0efdaace6f0aaa196da3cfdf51a4fdb154cf3043cd6b71252a62cf0823c
CANDIDATE_CONFIG_INPUT_HASH=e185476e13a0976ac227e84c486bd798ce0e6ae8753f98ead4d48a24036ac1a2
BASELINE_RESOLVED_CONFIG_HASH=61a457d9e36e595aa5b1b925910a43a14ebb11cede15154339495e1ad1ae72ce
CANDIDATE_RESOLVED_CONFIG_HASH=bc22ba532ffc69e05e6830ce32421e964c293aa307deb9c2999c4629ae605519
DATA_HASH=69e5a6f656356832f7e1fa6a9774bc404030f32874e18e57e0f38b6a309a1002
MAX_DATE=20220428
TEST_ROWS=0
SEED=0
MODE=valid-only
FULL_TRAINING_BUDGET=true
FORMAL_MAX_BATCHES=null
BASELINE_STATUS=COMPLETED_AND_AUDITED
CANDIDATE_STATUS=COMPLETED_AND_AUDITED
BASELINE_RUN_ID=run-20260831T134304010213Z-exp_003-420a5b16
CANDIDATE_RUN_ID=run-20260831T134427820061Z-exp_003-420a5b16
BASELINE_BATCHES_SEEN=470
CANDIDATE_BATCHES_SEEN=376
BASELINE_MANIFEST_SHA256=43b5974c6683b0e2f65f94f3030700a865f545fb1e3c218a20a74d18a00f7939
CANDIDATE_MANIFEST_SHA256=c90e6dc98f6d19aab049d600ccb89db9db73a9b9d6163d158f6253ba160915fb
BASELINE_PREDICTION_HASH=5bd21e55d1720efa77f9b4c5c76c9cfd0bbc816a29cd0dcd65e2e13ad4de587b
CANDIDATE_PREDICTION_HASH=f9c081a591ec16373d83eb0feb6f614cec79c4c2f71939fb724126568fadc83e
BASELINE_CHECKPOINT_HASH=41227be4df12bb17dcc77edad3d9b3a04f4b36474f8392757a75146397aacd34
CANDIDATE_CHECKPOINT_HASH=b01543055a57651b8601602ac8785f667985a9aae17e525dfa8fcd3e618177dd
BASELINE_CONTRACT=PASS
CANDIDATE_CONTRACT=PASS
BASELINE_PREDICTION_CONTRACT=PASS_124909_ROWS
CANDIDATE_PREDICTION_CONTRACT=PASS_124909_ROWS
BASELINE_AUDIT=PASS
CANDIDATE_AUDIT=PASS
RETRY_COUNT=0
PR25_EVIDENCE_USED=false
PREDICTIONS_MODIFIED=false
OFFICIAL_E_EVALUATION_PERFORMED=false
OFFICIAL_E_METRICS_PRODUCED=false
FORMAL_METRICS_PRODUCED=false
FINAL_APPROVAL_CREATED=false
test_access=false
NEXT_RECEIVER=E

## Frozen package paths

- Baseline: `C:\Users\asus-pc\Desktop\BOBAAA\BOB-AGENT\artifacts\public-campaign-private\exp003_420a5b16_baseline`
- Candidate: `C:\Users\asus-pc\Desktop\BOBAAA\BOB-AGENT\artifacts\public-campaign-private\exp003_420a5b16_candidate`

Each private directory contains the immutable completed manifest, validation
predictions, checkpoint, resolved config, training history, runner summary,
execution log, and exit status. No package file is copied into Git.

Both runs use the same clean producing commit, frozen data hash, unchanged
feature set, seed 0, and full approved training budget. Neither invocation
included `--max-batches`, `--synthetic-smoke`, or any test operation. The
runner generated its required internal validation summary, but B did not use
that summary for comparison, selection, or decision-making and does not report
metric values here. E must independently evaluate the immutable prediction
bytes through the approved valid-only route.

## Declared artifact SHA-256 inventory

Baseline:

- `valid_predictions.csv`: `5bd21e55d1720efa77f9b4c5c76c9cfd0bbc816a29cd0dcd65e2e13ad4de587b`
- `checkpoint.npz`: `41227be4df12bb17dcc77edad3d9b3a04f4b36474f8392757a75146397aacd34`
- `resolved_config.json`: `5977d6bc93adad91073d78e98ef012c59684805a1f45ce900d06cbcef43a083f`
- `training_history.json`: `c01077bbc8d5e023650e495450b7b6ff55dd38f7e09b2d90a7ba0e1051869818`
- `runner_metrics.json`: `0684a6ef0530a0546e2ffc3896afffe0e511cb67ce172b2b7551b4a53923d60c`

Candidate:

- `valid_predictions.csv`: `f9c081a591ec16373d83eb0feb6f614cec79c4c2f71939fb724126568fadc83e`
- `checkpoint.npz`: `b01543055a57651b8601602ac8785f667985a9aae17e525dfa8fcd3e618177dd`
- `resolved_config.json`: `8837a8710c72a3b02493af8e5de30440626ae7941e8893caa610cacd4b7b7474`
- `training_history.json`: `54970fa76e83212dffaeefd20c49b88567b9dcb94c7730d67ae2bc34a7db56d2`
- `runner_metrics.json`: `e4f1f192be9a61e880cf7a96687a233c18bb038558c707e150e698987617c5d7`

## B verification

- Both exact approved routes passed real-development preflight with 1,266,021
  rows, maximum date 20220428, binary labels, and zero later-split rows.
- The required unit suite passed 178 tests with four Windows symlink capability
  skips.
- Repository contracts, both protected-file verifiers, and the nine-test
  prediction-contract suite passed.
- Completed-manifest validation with artifact-byte verification passed for
  both package roots.
- Valid-only prediction validation passed both immutable prediction files at
  exactly 124,909 rows.
- `tools.audit_run` passed commit, clean-state, data-boundary, hash, route,
  artifact, and command checks for both manifests.
- `git diff --check` passed, no protected `starter/` file changed, and no data,
  prediction, checkpoint, credential, or generated artifact is included in
  this handoff change.

The single authorized exp_003 baseline/candidate pair is consumed. E alone may
perform the independent public-validation evaluation. Test and final release
remain forbidden.
