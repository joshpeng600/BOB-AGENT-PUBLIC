# exp_003 merged C/D setup integration review

STATUS=B_SYNTHETIC_PREFLIGHT_ALLOWED
ROLE=A
EXPERIMENT_ID=exp_003
BASE_MAIN_SHA=1dc25ed52430df9291f74697c843e1d7d9eb81e0
C_PR=13
C_SOURCE_COMMIT_SHA=ccaa4a670ca853e4e96f9c383f12679164605611
D_PR=15
D_IMPLEMENTATION_COMMIT_SHA=76c7f2ec2ae3867ed33b66f2209090edded0b60a
D_READINESS_COMMIT_SHA=7575140a1d5c5cb7ead5c0e767177087a2052dce
BASELINE_CONFIG=configs/approved/exp_001.json
BASELINE_CONFIG_SHA256=5221e0efdaace6f0aaa196da3cfdf51a4fdb154cf3043cd6b71252a62cf0823c
CANDIDATE_CONFIG=configs/candidates/bpr_fm_dim32.json
CANDIDATE_CONFIG_SHA256=e185476e13a0976ac227e84c486bd798ce0e6ae8753f98ead4d48a24036ac1a2
EXPERIMENT_SPEC=experiments/exp_003.json
EXPERIMENT_SPEC_SHA256=79c0e54f962c84213c0150474894ff695d5d6acfed85aa2955abb173b425f20c
SINGLE_SCIENTIFIC_CHANGE=model.embedding_dim:16->32
CONFIG_DIFF_CHECK=PASS
DATA_HASH=69e5a6f656356832f7e1fa6a9774bc404030f32874e18e57e0f38b6a309a1002
DATA_AND_FEATURES_UNCHANGED=true
MAXIMUM_DEVELOPMENT_DATE=20220428
TEST_ROWS=0
SYNTHETIC_SMOKE_ALLOWED=true
SYNTHETIC_SMOKE_MAX_BATCHES=1
REAL_VALID_RUN_ALLOWED=false
AUTHORIZED_REAL_ATTEMPTS_ACTIVE=0
REAL_DATA_TRAINING_PERFORMED=false
FORMAL_METRICS_PRODUCED=false
PR25_EVIDENCE_USED=false
FINAL_APPROVAL_CREATED=false
test_access=false
NEXT_RECEIVER=B

## A decision

A reviewed the C feasibility evidence merged by PR #13 and the D config-only
candidate and readiness evidence merged by PR #15 on clean public main
`1dc25ed52430df9291f74697c843e1d7d9eb81e0`.

C confirms the frozen development manifest hash, unchanged data and feature
definitions, train-only fitting and pair sampling, valid-only evaluation,
maximum development date 20220428, zero test rows, and feasible parameter-state
growth. C performed no training and produced no formal metric.

D's candidate is present on merged main. A performed a recursive structured
comparison of the scientific configuration fields in the accepted exp_001
baseline and the exp_003 candidate. The only difference is
`model.embedding_dim: 16 -> 32`. Model family, objective, sampling, features,
seed, batch size, epochs, patience, `max_batches`, data mode, allowed splits,
development cutoff, and evaluation split are unchanged.

The merged C and D prerequisites therefore pass setup integration. B may now
verify the exact config and contract binding and run at most one explicit
one-batch synthetic smoke. Synthetic evidence proves interface operability only.
It does not authorize real-data training, formal validation metrics, hidden-test
access, champion promotion, or final approval.

After B evidence merges, E must independently pre-review the integrated route.
Only after merged B and E readiness may A consider a separate exact
`REAL_VALID_RUN_ALLOWED` gate under the bounded campaign authorization.
