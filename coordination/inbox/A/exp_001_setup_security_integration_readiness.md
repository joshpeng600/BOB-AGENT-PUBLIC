# exp_001 setup security integration readiness

STATUS=READY_FOR_PR_MERGE_AND_POST_MERGE_E_REREVIEW
ROLE=A
REVIEWED_MAIN_SHA=28d4d7480c0a76d5076dc10e694898188af99473
B_IMPLEMENTATION_SHA=5cc237161909b592df0bdb24a8c6f47543c77e92
B_READINESS_SHA=6a73236e8d3e11aa9687f7d44ed7cbb97aed6110
E_IMPLEMENTATION_SHA=6ee8e268e4d07af3224f933da4e194644c0b1273
E_READINESS_SHA=8fae2557219030f2429ed1ca29d6469f62ea2735
A_INTEGRATION_FIX_SHA=60440cbf98f81f199f9045b87918cb4439a4169b

## Integrated setup decisions

- B binds completed manifests to the approved experiment specification identity, status, candidate/baseline route, raw specification and configuration bytes, resolved configuration, and runtime inputs.
- E audits the same approved repository route through fixed ordinary-file handles and rejects input replacement.
- E evaluates predictions from a private snapshot created from one no-follow ordinary-file handle, and verifies the source binding and bytes after evaluation.
- C real-data readiness remains confirmed with manifest SHA-256 `69e5a6f656356832f7e1fa6a9774bc404030f32874e18e57e0f38b6a309a1002`, maximum date `20220428`, zero test rows, passing preflight, and verified same-user pair feasibility.
- D model and training interfaces remain confirmed; no scientific logic change was required.

## Clean combined verification

PYTEST=PASS_106
UNITTEST=PASS_106_OF_106
REPOSITORY_CONTRACTS=PASS
PROTECTED_HASHES=PASS
PREDICTION_CONTRACT=PASS_9_OF_9
STARTER_CHANGED=false
REAL_DATA_TRAINING_PERFORMED=false
FORMAL_VALID_METRICS_PRODUCED=false
PR25_EVIDENCE_USED=false
TEST_ACCESS=false

## Remaining gate

This record is pre-merge integration evidence, not permission to run. The integrated repair must merge to `main` through the approved PR gate with all four Actions checks passing. E must then independently rereview the resulting clean `main`. Only a later A-owned state change may set `REAL_VALID_RUN_ALLOWED=ALLOWED` for the one already-authorized fresh valid-only baseline/candidate pair.

NEXT_RECEIVER=HUMAN_FOR_MERGE
