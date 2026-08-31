# exp_003 real-valid cycle gate activation — A

STATUS=REAL_VALID_RUN_ALLOWED
ROLE=A
AUTHORIZED_AT_UTC=2026-08-31T13:07:24Z
BASE_MAIN_SHA=58962df016da5808236b73d135a7abdd1d3fe879
EXPERIMENT_ID=exp_003
AUTHORIZED_ATTEMPTS=1
RUN_PAIR=baseline,candidate
BASELINE_CONFIG=configs/approved/exp_001.json
CANDIDATE_CONFIG=configs/candidates/bpr_fm_dim32.json
EXPERIMENT_SPEC_HASH=79c0e54f962c84213c0150474894ff695d5d6acfed85aa2955abb173b425f20c
BASELINE_CONFIG_HASH=5221e0efdaace6f0aaa196da3cfdf51a4fdb154cf3043cd6b71252a62cf0823c
CANDIDATE_CONFIG_HASH=e185476e13a0976ac227e84c486bd798ce0e6ae8753f98ead4d48a24036ac1a2
DATA_HASH=69e5a6f656356832f7e1fa6a9774bc404030f32874e18e57e0f38b6a309a1002
SINGLE_SCIENTIFIC_CHANGE=model.embedding_dim:16->32
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

The repository owner's bounded campaign authorization permits automatic
public-validation use for exp_003 through exp_005 while requiring a separate A
evidence gate for every experiment. That authorization is recorded in
`coordination/inbox/A/exp_003_005_bounded_campaign_authorization_20260831.md`
and `coordination/current_state.json`. It never permits hidden-test access or
final approval.

E's independent exp_003 pre-evaluation readiness is merged in PR #19 at
`58962df016da5808236b73d135a7abdd1d3fe879`. This record therefore activates
exactly one exp_003 full-budget valid-only baseline/candidate pair against that
exact main SHA. It is not standing authority for another pair or experiment.

## Satisfied prerequisites

- C PR #13 is merged as `5444bcdc24ad1d587b7dbcfe375b90d3f238ddd6`
  and confirms unchanged features, development-data hash
  `69e5a6f656356832f7e1fa6a9774bc404030f32874e18e57e0f38b6a309a1002`,
  maximum development date 20220428, zero later-split rows, and no leakage.
- D PR #15 is merged as `1dc25ed52430df9291f74697c843e1d7d9eb81e0`
  and supplies the config-only candidate. The sole scientific change is
  `model.embedding_dim: 16 -> 32`.
- B PR #17 is merged as `0b0ab600d835c32c2bfa49c74863048b66e5bd5a`
  and reports exact route/config binding plus one successful one-batch
  synthetic-only smoke with zero retries.
- E PR #19 is merged as `58962df016da5808236b73d135a7abdd1d3fe879`
  with `PRE_EVALUATION_READY`. Route and config binding, full-budget
  enforcement, synthetic/formal isolation, immutable prediction ingress,
  valid-only isolation, protected hashes, and test isolation pass.

Each prerequisite PR completed the four required GitHub Actions checks. No
prerequisite role produced an exp_003 formal metric or accessed test.

## Exact permission

B may execute exactly one fresh baseline/candidate pair from one clean frozen
descendant of the base main SHA above. Both runs must bind the same producing
commit, development-data hash, unchanged feature set, seed 0, and full approved
training budget with formal `max_batches=null`. Each run has a 3600-second
limit. The baseline is `configs/approved/exp_001.json`; the candidate is
`configs/candidates/bpr_fm_dim32.json`.

One automatic repair attempt is permitted only for an already whitelisted
transient infrastructure failure with identical commit, commands, configs,
data, seed, and budget. Contract or hash mismatch, timeout, missing dependency,
NaN/Inf, leakage, dirty state, scientific failure, policy failure, and test
access are not auto-repairable.

PR #25 evidence remains permanently quarantined. This gate creates no final
approval, allows no test command, and authorizes no protected-file or
scientific change.

## Required handoff

B must hand both immutable formal packages and all declared hashes to E. E
alone performs the independent public-validation evaluation. A will make no
exp_003 model decision until E's complete evaluation evidence is merged.
