# exp_002 real-valid cycle gate activation — A

STATUS=REAL_VALID_RUN_ALLOWED
ROLE=A
BASE_MAIN_SHA=a673dbab096aabc19d3e3b8c877b80f03aaccdb3
EXPERIMENT_ID=exp_002
AUTHORIZED_ATTEMPTS=1
RUN_PAIR=baseline,candidate
BASELINE_CONFIG=configs/approved/exp_001.json
CANDIDATE_CONFIG=configs/candidates/bpr_fm_neg2.json
EXPERIMENT_SPEC_HASH=c3d1257751d2abf15d62a0638679efe892cc13a8ff3325630ab2acbbece5c8c9
BASELINE_CONFIG_HASH=5221e0efdaace6f0aaa196da3cfdf51a4fdb154cf3043cd6b71252a62cf0823c
CANDIDATE_CONFIG_HASH=4ae653c2a68c1dc461ff2149540920e009355637e22e557b70c68e41460d2b61
DATA_HASH=69e5a6f656356832f7e1fa6a9774bc404030f32874e18e57e0f38b6a309a1002
SEED=0
MODE=valid-only
FULL_TRAINING_BUDGET=true
FORMAL_MAX_BATCHES=null
MAX_RUNTIME_SECONDS_PER_RUN=3600
SAME_COMMIT_REQUIRED=true
SAME_DATA_HASH_REQUIRED=true
SAME_FEATURE_SET_REQUIRED=true
SAME_SEED_REQUIRED=true
SAME_TRAINING_BUDGET_REQUIRED=true
PR25_EVIDENCE_USED=false
FORMAL_METRICS_PRODUCED=false
FINAL_APPROVAL_CREATED=false
test_access=false
NEXT_RECEIVER=B

## Authorization basis

The repository owner explicitly instructed the team to complete E's
pre-review, have A open the gate, and then continue B's work. E's independent
pre-evaluation review is merged in PR #48 at
`a673dbab096aabc19d3e3b8c877b80f03aaccdb3`. This is exact authorization for
one exp_002 full-budget valid-only baseline/candidate pair. It is not standing
authority and does not authorize test access, final release, extra scientific
changes, protected-file changes, or additional pairs.

## Satisfied prerequisites

- C PR #45 is merged as `c5280a1b434f314420e7add028a67414166803f6`
  and confirms the unchanged development-data hash, maximum date 20220428,
  zero test rows, valid row order, and same-user pair feasibility.
- D config delivery PR #46 is merged as
  `7bf6cdc188d952a56563a06662ffbbe9b1d4c720` under the recorded one-time
  config-only delegation. B and E independently verified the resulting
  configuration. The only scientific change is
  `objective.negatives_per_positive: 1 -> 2`.
- B PR #47 is merged as `8d4a03c0c507d03321e51a1190b6038abe13ac0a`.
  It binds the approved exp_001 BPR champion as baseline, binds the exp_002
  two-negative candidate, and reports both one-batch synthetic routes PASS.
- E PR #48 is merged as `a673dbab096aabc19d3e3b8c877b80f03aaccdb3`
  with `PRE_EVALUATION_READY`. Route/config fail-closed behavior,
  synthetic/formal isolation, immutable prediction ingress, valid-only
  isolation, all protected hashes, and the four required GitHub checks pass.

Each of PRs #45 through #48 completed all four required GitHub Actions checks.
No prerequisite role performed a formal exp_002 run, produced a formal metric,
read PR #25 evidence, or accessed test.

## Exact permission

B may execute exactly one fresh baseline/candidate pair from one clean frozen
descendant of the base main SHA above. Both runs must bind the same producing
commit, development-data hash, unchanged feature set, seed 0, and full approved
training budget with formal `max_batches=null`. The baseline route is
`configs/approved/exp_001.json`; the candidate route is
`configs/candidates/bpr_fm_neg2.json`. Each run has a 3600-second limit.

One automatic repair attempt is permitted only for an already whitelisted
transient infrastructure failure with the exact same command, commit, config,
data, seed, and budget. Missing dependencies, timeout, dirty state, contract or
hash mismatch, NaN/Inf, leakage, scientific failure, policy failure, and test
access are not auto-repairable. A failed or incomplete attempt never silently
creates a new scientific pair authorization.

PR #25 artifacts and metrics remain permanently quarantined and must not be
read, copied, reused, compared, or treated as evidence. This gate creates no
final approval and permits no test command.

## Required handoff

B must provide both immutable formal packages, complete manifests,
predictions, checkpoints, resolved configs, training histories, runner
evidence, and every declared SHA-256 to E. E alone performs the independent
formal valid evaluation. A will make no exp_002 decision before E returns
complete independently verified evidence.
