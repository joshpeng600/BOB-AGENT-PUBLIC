# exp_001 real-valid cycle gate activation — A

STATUS=REAL_VALID_RUN_ALLOWED
ROLE=A
BASE_MAIN_SHA=ed44036eaed05bb3e00792f65c20849bb22af476
EXPERIMENT_ID=exp_001
AUTHORIZED_ATTEMPTS=1
RUN_PAIR=baseline,candidate
BASELINE_CONFIG=configs/approved/baseline_fm.json
CANDIDATE_CONFIG=configs/candidates/bpr_fm.json
DATA_HASH=69e5a6f656356832f7e1fa6a9774bc404030f32874e18e57e0f38b6a309a1002
SEED=0
MODE=valid-only
FULL_TRAINING_BUDGET=true
FORMAL_MAX_BATCHES=null
SAME_COMMIT_REQUIRED=true
SAME_DATA_HASH_REQUIRED=true
SAME_FEATURE_SET_REQUIRED=true
SAME_SEED_REQUIRED=true
SAME_TRAINING_BUDGET_REQUIRED=true
PR25_EVIDENCE_USED=false
FORMAL_METRICS_PRODUCED=false
test_access=false
NEXT_RECEIVER=B

## Authorization basis

The repository owner explicitly authorized the acting A integration agent to
open this exact gate after the real-data training scope and safeguards were
stated. This is not standing authority and does not permit extra attempts,
scientific-logic changes, protected-file changes, test access, or final
approval.

PR #37 merged as `ed44036eaed05bb3e00792f65c20849bb22af476`
after all four required GitHub checks passed. Its E phase-one evidence records
`PRE_EVALUATION_READY`, 121/121 clean unit tests, all seven protected hashes,
9/9 prediction-contract checks, and 27 repository JSON contracts plus JSONL and
TOML checks. E did not train or produce formal metrics in phase one.

## Exact permission

B may execute exactly one fresh formal baseline/candidate pair. Both runs must
be produced from one clean frozen descendant of the base SHA above and bind the
same development-data hash, unchanged feature set, seed 0, and full approved
training budget. The baseline route is
`configs/approved/baseline_fm.json`; the candidate route is
`configs/candidates/bpr_fm.json`.

The previously quarantined PR #25 artifacts and metrics must not be read,
copied, reused, compared, or treated as evidence. No command may score or
access test. A failed or incomplete attempt does not silently grant another
attempt; any retry outside the experiment contract requires a new recorded
decision.

## Required handoff and next gate

B must provide both immutable formal packages, complete manifests, predictions,
checkpoints, resolved configs, training histories, runner evidence, and every
declared SHA-256 to E. E will independently audit and atomically evaluate only
valid using the protected evaluator. A will not decide the experiment until E
returns complete baseline and candidate evidence. This record does not create
or approve a final release approval.
