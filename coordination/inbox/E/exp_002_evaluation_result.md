# exp_002 independent formal valid evaluation

STATUS=VALID_IMPROVEMENT_REJECTED
ROLE=E
PHASE=FORMAL_VALID_EVALUATION
EXPERIMENT_ID=exp_002
EVALUATION_COMMIT_SHA=a5bd90a2f25dc39bc8bffb2c5003afce59a59f9c
BASELINE_RUN_COMMIT_SHA=fced9a79ae3e06af69e06d319ee316e77fcce98a
CANDIDATE_RUN_COMMIT_SHA=fced9a79ae3e06af69e06d319ee316e77fcce98a
DATA_HASH=69e5a6f656356832f7e1fa6a9774bc404030f32874e18e57e0f38b6a309a1002
BASELINE_PREDICTION_HASH=5bd21e55d1720efa77f9b4c5c76c9cfd0bbc816a29cd0dcd65e2e13ad4de587b
CANDIDATE_PREDICTION_HASH=4b4105631ffff4543f7e66965138b8ecd2bd44151da9ccac90d4282ea616ed9e
BASELINE_CHECKPOINT_HASH=a8c232704c417c8493bce12fc7f27a31431eabfc85d08fc076669df528b63f85
CANDIDATE_CHECKPOINT_HASH=1f0934e5e758896ac595c8e8ae26791b0a36dd479c6fc4fdc6a70d9b61aeb997
BASELINE_CONFIG_INPUT_HASH=5221e0efdaace6f0aaa196da3cfdf51a4fdb154cf3043cd6b71252a62cf0823c
CANDIDATE_CONFIG_INPUT_HASH=4ae653c2a68c1dc461ff2149540920e009355637e22e557b70c68e41460d2b61
BASELINE_RESOLVED_CONFIG_HASH=6ba29a9cd553ccdaf6624ac7835a8143603329504b03b6c2f40d376f35988ed8
CANDIDATE_RESOLVED_CONFIG_HASH=5ee103e57bdf6b1679a21f671869f937e76e6f4b5439bb2f0db271b5b20e3a3f
ARTIFACT_AUDIT=PASS_BOTH
IMMUTABLE_SNAPSHOT=PASS_BOTH
BASELINE_GAUC=0.6705350761953585
BASELINE_NDCG_AT_5=0.5372069380698954
BASELINE_PRIMARY=0.603871007132627
CANDIDATE_GAUC=0.6699810327038805
CANDIDATE_NDCG_AT_5=0.5365399077545753
CANDIDATE_PRIMARY=0.6032604702292279
PRIMARY_DELTA_CANDIDATE_MINUS_BASELINE=-0.0006105369033990726
ABSOLUTE_PRIMARY_DELTA=0.0006105369033990726
ACCEPTANCE_THRESHOLD_STRICT_GT=0.605871007132627
CANDIDATE_MINUS_ACCEPTANCE_THRESHOLD=-0.0026105369033990744
THRESHOLD_CHECK=FAIL
RETAINED_CHAMPION_EXPERIMENT_ID=exp_001
RETAINED_CHAMPION_PRIMARY=0.603871007132627
evaluator_role=E
PREDICTIONS_MODIFIED=false
TRAINING_PERFORMED=false
PR25_EVIDENCE_USED=false
RUNNER_METRICS_VALUES_USED=false
FORMAL_EVALUATION_PERFORMED=true
FORMAL_METRICS_PRODUCED=true
FINAL_APPROVAL_CREATED=false
test_access=false
NEXT_RECEIVER=A

## Independent conclusion

The exp_002 candidate is rejected. Its valid primary score
`0.6032604702292279` does not exceed the human-approved strict threshold
`0.605871007132627`. The candidate is also below the same-pair baseline by
`0.0006105369033990726`. The exp_001 champion remains unchanged at
`0.603871007132627`.

This is a validation-only research decision. It is not a final release
approval and does not authorize test access.

## Official E metrics

| Run | GAUC | nDCG@5 | Primary |
| --- | ---: | ---: | ---: |
| exp_001 approved baseline | 0.6705350761953585 | 0.5372069380698954 | 0.603871007132627 |
| exp_002 candidate, negatives_per_positive=2 | 0.6699810327038805 | 0.5365399077545753 | 0.6032604702292279 |

Both primary values exactly equal the arithmetic mean of GAUC and nDCG@5.
The values above were independently produced by the protected
`tools/safe_evaluate.py` valid-only route using protected official evaluator
SHA-256 `ecfde28392eb14fec4f488083251df50624e1af2b86278b962daecfb42d195de`.
B self-reported metric values and `runner_metrics.json` metric values were not
used for this result.

## Immutable artifact audit

- Both manifests bind producing commit
  `fced9a79ae3e06af69e06d319ee316e77fcce98a`, data hash
  `69e5a6f656356832f7e1fa6a9774bc404030f32874e18e57e0f38b6a309a1002`,
  seed 0, the same FM model/features/training budget, `mode=valid-only`, and
  `max_batches=null`.
- Both run-manifest contracts passed with all five declared artifact bytes
  verified. Independent frozen-commit `tools.audit_run` passed both packages.
- Every actual package file was SHA-256 inventoried. `runner_metrics.json` was
  treated only as a required byte-hash artifact; its metric values were not
  read or used.
- Both predictions passed the strict header
  `row_id,user_id,video_id,score`, contiguous row IDs from 0, finite scores,
  and exact official-valid user/video alignment at 124,909 rows. No
  deduplication was performed.
- Prediction SHA-256 values were unchanged before and after evaluation.
- The development dataset manifest has `max_date=20220428`, `test_rows=0`,
  and the exact recorded data hash.

The first safe-evaluation invocation failed closed before evaluator execution
because the temporary output directory had not been created. One permitted
infrastructure-only retry corrected the directory-creation syntax and reused
identical scientific and evaluation inputs. No timeout or partial metric
evidence occurred.

## Evidence paths

- `reports/evaluation/exp_002_fced9a7_baseline_metrics.json`
- `reports/evaluation/exp_002_fced9a7_candidate_metrics.json`
- `reports/evaluation/exp_002_fced9a7_artifact_audit.json`
- `coordination/results/exp_002_evaluation.json`
- `coordination/inbox/E/exp_002_fced9a7_b_handoff.md`
