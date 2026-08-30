# exp_001 fresh formal valid evaluation — isolated E

STATUS=VALID_IMPROVEMENT_ACCEPTED_PENDING_A_PROCESS_INCIDENT_REVIEW
ROLE=E
PHASE=FORMAL_VALID_EVALUATION
EXPERIMENT_ID=exp_001
EVALUATION_COMMIT_SHA=44fd36aa9b35b7fc9c01389e6dd453e972f16635
BASELINE_RUN_COMMIT_SHA=44fd36aa9b35b7fc9c01389e6dd453e972f16635
CANDIDATE_RUN_COMMIT_SHA=44fd36aa9b35b7fc9c01389e6dd453e972f16635
DATA_HASH=69e5a6f656356832f7e1fa6a9774bc404030f32874e18e57e0f38b6a309a1002
BASELINE_PREDICTION_HASH=56d317930cd4bacb0fae0f6c6798834a440bc2a6c5a991a50c1ce81f406b86dc
CANDIDATE_PREDICTION_HASH=d137ce7d482d2cb8a2042d59831fa1fd1b1de50abd93bef288c189e11e05c0e3
ARTIFACT_AUDIT=PASS_BOTH
IMMUTABLE_SNAPSHOT=PASS_BOTH
BASELINE_GAUC=0.6671326321610643
BASELINE_NDCG_AT_5=0.5358048805448538
BASELINE_PRIMARY=0.601468756352959
CANDIDATE_GAUC=0.6705350761953585
CANDIDATE_NDCG_AT_5=0.5372069380698954
CANDIDATE_PRIMARY=0.603871007132627
PRIMARY_DELTA=0.0024022507796679
IMPROVEMENT_RULE_CHECK=PASS_STRICT_DELTA_GT_0.002
ABSOLUTE_THRESHOLD_CHECK=PASS_CANDIDATE_GT_0.6036
ISOLATED_E_PR25_EVIDENCE_USED=false
ORCHESTRATOR_PR25_READ_AFTER_BOTH_RUNS=true
PREDICTIONS_MODIFIED=false
TRAINING_PERFORMED=false
FORMAL_EVALUATION_PERFORMED=true
FORMAL_METRICS_PRODUCED=true
FINAL_APPROVAL_CREATED=false
test_access=false
NEXT_RECEIVER=A

## Independent conclusion

The fresh same-user BPR candidate passes the approved valid-only success rule.
Its primary score exceeds the same-commit baseline by
`0.0024022507796679`, strictly greater than `0.002`, and the candidate primary
`0.603871007132627` exceeds the experiment specification threshold `0.6036`.

Both primary values exactly equal the arithmetic mean of GAUC and nDCG@5.
This is a validation research conclusion only. It is not a final release
approval and does not permit test access.

## Fresh immutable evidence

| Run | GAUC | nDCG@5 | Primary |
| --- | ---: | ---: | ---: |
| Approved baseline FM | 0.6671326321610643 | 0.5358048805448538 | 0.601468756352959 |
| Same-user BPR FM | 0.6705350761953585 | 0.5372069380698954 | 0.603871007132627 |

- Both formal manifests bind clean producing commit
  `44fd36aa9b35b7fc9c01389e6dd453e972f16635`, data hash
  `69e5a6f656356832f7e1fa6a9774bc404030f32874e18e57e0f38b6a309a1002`,
  seed 0, unchanged FM features, and full budget with `max_batches=null`.
- Both run-manifest contracts and independent byte/hash audits passed.
- Both predictions passed exact official-valid alignment at 124,909 rows.
- Prediction SHA-256 values were identical before and after evaluation.
- Protected official evaluator SHA-256:
  `ecfde28392eb14fec4f488083251df50624e1af2b86278b962daecfb42d195de`.
- Evaluation was valid-only; no approval file was created or used.

## Isolation and process incident disclosure

The E evaluation was performed by a fresh sub-agent with no inherited
conversation context. It was explicitly prohibited from reading or using PR
#25 or any old formal metrics and reported
`PR25_EVIDENCE_USED=false`, `PREDICTIONS_MODIFIED=false`,
`TRAINING_PERFORMED=false`, and `test_access=false`.

Separately, after both B runs and hashes were complete, the coordinating root
session accidentally opened the quarantined PR #25 metrics while searching for
an output schema. That session was immediately removed from E scoring. The
read could not influence the already completed training or frozen predictions,
and the isolated E evaluator did not inherit it. A must retain and explicitly
disposition this contained, non-causal process incident; E makes no governance
exception.

## Verification

- Relevant E/security tests: PASS, 75/75.
- Fresh safe evaluation output contracts: PASS for baseline and candidate.
- Protected-file canonical registry and evaluator manifest: PASS.
- Full discovery in the isolated evaluator environment executed 84 tests; six
  modules could not import because that isolated Python lacked NumPy. No
  executed test failed. The producing environment's clean pre-gate suite had
  already passed 121/121 on the same protected toolchain.
- Default `tools/verify_protected_files.py` remains incompatible with the
  governance registry's `files` array shape; canonical seven-file verification
  and the protected evaluator manifest both passed.

## Evidence paths

- `reports/evaluation/exp_001_fresh_44fd36_baseline_metrics.json`
- `reports/evaluation/exp_001_fresh_44fd36_candidate_metrics.json`
- `coordination/inbox/E/exp_001_fresh_44fd36_b_handoff.md`
- Local Git-ignored packages under
  `artifacts/exp_001_formal_44fd36_baseline` and
  `artifacts/exp_001_formal_44fd36_candidate`
