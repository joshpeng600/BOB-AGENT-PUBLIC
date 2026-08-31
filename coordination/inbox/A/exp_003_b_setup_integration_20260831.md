# exp_003 B synthetic-readiness integration

STATUS=READY_FOR_E_PRE_EVALUATION_REVIEW
ROLE=A
REVIEWED_AT_UTC=2026-08-31T12:53:34Z
REVIEWED_MAIN_SHA=0b0ab600d835c32c2bfa49c74863048b66e5bd5a
EXPERIMENT_ID=exp_003
B_PR=17
B_SOURCE_COMMIT_SHA=a3ec225ecd82bbc96fdad68b776da666b540304d
B_MERGE_COMMIT_SHA=0b0ab600d835c32c2bfa49c74863048b66e5bd5a
B_READINESS=coordination/inbox/B/exp_003_setup_readiness.md
C_PR=13
D_PR=15
BASELINE_CONFIG=configs/approved/exp_001.json
CANDIDATE_CONFIG=configs/candidates/bpr_fm_dim32.json
SINGLE_SCIENTIFIC_CHANGE=model.embedding_dim:16->32
CONFIG_DIFF_CHECK=PASS
SYNTHETIC_SMOKE_STATUS=PASS_SYNTHETIC_ONLY
SYNTHETIC_BATCHES_SEEN=1
SYNTHETIC_RETRY_COUNT=0
REAL_DATA_ACCESSED=false
REAL_DATA_TRAINING_PERFORMED=false
REAL_VALID_RUN_ALLOWED=false
FORMAL_METRICS_PRODUCED=false
PR25_EVIDENCE_USED=false
FINAL_APPROVAL_CREATED=false
test_access=false
NEXT_RECEIVER=E

## A integration decision

A accepts the merged B readiness from PR #17 as synthetic interface evidence
only. B bound the merged exp_003 experiment spec to the approved exp_001
baseline and the `bpr_fm_dim32` candidate, verified that the sole scientific
change is `model.embedding_dim: 16 -> 32`, and consumed the single authorized
one-batch synthetic smoke with zero retries. The smoke did not access the real
development dataset and is not formal metric evidence.

The merged C feasibility evidence from PR #13, D config-only readiness from PR
#15, and B synthetic readiness from PR #17 are now available for E's
independent pre-evaluation review. E must independently verify route and config
binding, full-budget enforcement, immutable prediction ingress, valid-only
evaluation, and test isolation. E must not train, score a formal package,
modify predictions, create formal metrics or final approval, or access test.

This integration does not open the real validation gate. After E readiness is
merged, A must record a separate exact full-SHA
`REAL_VALID_RUN_ALLOWED=ALLOWED` decision under the bounded campaign
authorization before B may read real development data or produce a formal
baseline/candidate pair.

## Evidence accepted

- B readiness source commit:
  `a3ec225ecd82bbc96fdad68b776da666b540304d`.
- B readiness merge commit:
  `0b0ab600d835c32c2bfa49c74863048b66e5bd5a`.
- Synthetic run manifest SHA-256:
  `5be93891c0a425d4b900418b742dfecbd80eae857561290c8ba4c8a3b124c490`.
- Repository contracts, protected hashes, prediction contract, and required
  unit suite passed in B evidence; PR #17 passed all four required GitHub
  checks.

No data, prediction, checkpoint, credential, or generated run artifact is
included in this integration change.
