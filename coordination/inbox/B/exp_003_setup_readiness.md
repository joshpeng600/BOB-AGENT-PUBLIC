# exp_003 exact-config preflight and synthetic readiness

STATUS=READY_FOR_A_INTEGRATION_REVIEW
AUTHOR_ROLE=B
EXPERIMENT_ID=exp_003
COMMIT_SHA=b0abb6215186d53bc54f7baa8761f2e515ff6b4d
APPROVED_AGAINST_COMMIT_SHA=1dc25ed52430df9291f74697c843e1d7d9eb81e0
BASELINE_CONFIG=configs/approved/exp_001.json
BASELINE_CONFIG_SHA256=5221e0efdaace6f0aaa196da3cfdf51a4fdb154cf3043cd6b71252a62cf0823c
CANDIDATE_CONFIG=configs/candidates/bpr_fm_dim32.json
CANDIDATE_CONFIG_SHA256=e185476e13a0976ac227e84c486bd798ce0e6ae8753f98ead4d48a24036ac1a2
EXPERIMENT_SPEC=experiments/exp_003.json
EXPERIMENT_SPEC_SHA256=79c0e54f962c84213c0150474894ff695d5d6acfed85aa2955abb173b425f20c
SINGLE_SCIENTIFIC_CHANGE=model.embedding_dim:16->32
CONFIG_DIFF_CHECK=PASS
SYNTHETIC_SMOKE_STATUS=PASS_SYNTHETIC_ONLY
SYNTHETIC_SMOKE_MAX_BATCHES=1
SYNTHETIC_BATCHES_SEEN=1
SYNTHETIC_RETRY_COUNT=0
SYNTHETIC_RUN_MANIFEST_SHA256=5be93891c0a425d4b900418b742dfecbd80eae857561290c8ba4c8a3b124c490
LARGE_ARTIFACT_PATH=/private/tmp/bob-exp003-b-synthetic.YGYmAf/run
REAL_DATA_ACCESSED=false
REAL_DATA_TRAINING_PERFORMED=false
REAL_VALID_RUN_ALLOWED=false
FORMAL_METRICS_PRODUCED=false
PR25_EVIDENCE_USED=false
FINAL_APPROVAL_CREATED=false
test_access=false
NEXT_RECEIVER=A

## Scope and result

B verified the exact merged exp_003 route on clean commit
`b0abb6215186d53bc54f7baa8761f2e515ff6b4d`. The repository experiment spec
binds the accepted exp_001 baseline and the exp_003 candidate, and a recursive
comparison of the scientific fields found exactly one difference:
`model.embedding_dim: 16 -> 32`.

B then executed the one authorized candidate smoke with an explicit
`--max-batches 1 --synthetic-smoke` bound. The runner resolved the candidate
route, used the `same_user_bpr` objective, observed exactly one batch, recorded
zero retries, retained `test_access=false`, and emitted a contract-valid
`synthetic_only` manifest. The fixture was generated solely from the repository
synthetic test helper in a temporary private directory. It contained only the
fixed train/public-validation date windows and no real data.

This result proves interface operability only. It is not formal validation
evidence, does not support a model-quality claim, and does not open the real
validation gate. No real dataset was accessed, no formal metric was produced,
and neither hidden-test access nor final approval occurred.

## Immutable bindings and private artifact handoff

The synthetic package remains outside Git at
`/private/tmp/bob-exp003-b-synthetic.YGYmAf/run`. Its manifest SHA-256 is
`5be93891c0a425d4b900418b742dfecbd80eae857561290c8ba4c8a3b124c490`.
The manifest binds the following generated files without committing them:

- `checkpoint.npz`: `bb786f37ee13a87efe1e4c80defa6795889ec8849663c72e8cb4d978a4e77f82`
- `valid_predictions.csv`: `ba325cba8c2c8caa7e16f27244081a40fecb6f80fb297afc8ce8c7adba9f020f`
- `resolved_config.json`: `91714963206dfc7cce46e12c2b94050da0ca1dacd12a8b7ef8caec4015645f18`
- `training_history.json`: `f9d5c117d3185643081007a0e5521e48e8d3800625de855c214557a007ef1dc9`
- `runner_metrics.json`: `cdfbe206cfcd31b2b9c650100f4d0fb086e75b4db4e88ea4ea97de60a2f6e599`

No generated data, prediction, checkpoint, credential, or run artifact is
included in this change.

## Checks

All Python commands used the required repository interpreter at
`/Users/pengrenzhong/Documents/GitHub/BOB-AGENT/.venv/bin/python`.

- Experiment-spec contract: PASS.
- Repository contracts: PASS, 53 JSON files plus JSONL/TOML validated.
- Protected-file verification: PASS, all seven pinned files matched.
- Prediction-contract tests: PASS, 9/9.
- Required unit suite: PASS, 175/175.
- Structured scientific config diff: PASS, exactly one changed field.
- Synthetic run-manifest contract: PASS.
- `git diff --check`: PASS.
- `git diff -- starter/`: PASS, empty.

## Remaining gates

This readiness record must merge before E performs its independent setup
review. A must later record a separate exact `REAL_VALID_RUN_ALLOWED` gate
before B may access real development data or execute any formal validation run.
Test access and final release remain forbidden.
