# exp_001 formal valid evaluation — E

STATUS=VALID_IMPROVEMENT_ACCEPTED
ROLE=E
EXPERIMENT_ID=exp_001
PRODUCING_COMMIT_SHA=cb61b52affd5ecdb4095312087400fb482d8301b
PR_22_MERGED=true
ARTIFACT_AUDIT=PASS
PREDICTION_CONTRACT=PASS
PROTECTED_FILES=PASS
BASELINE_PRIMARY=0.601468756352959
CANDIDATE_PRIMARY=0.603871007132627
PRIMARY_DELTA=0.002402250779668
MINIMUM_IMPROVEMENT=0.002
CANDIDATE_THRESHOLD=0.6036
SUCCESS_RULE=PASS
FORMAL_EVALUATION_PERFORMED=true
FORMAL_METRICS_PRODUCED=true
FINAL_APPROVAL_CREATED=false
test_access=false
MANUAL_INTERVENTIONS=1
GOVERNANCE_RECORD_PENDING=true

## Decision

The independently evaluated same-user BPR candidate passes the approved valid
success rule. Its primary score improves over the same-commit, same-data,
same-seed baseline by `0.002402250779668`, which is greater than the required
strict improvement of `0.002`. Its primary score `0.603871007132627` also
exceeds the experiment specification's absolute threshold of `0.6036`.

This is a validation-only research conclusion. It is not a final release
approval and does not authorize test access.

## Immutable inputs and provenance

- The baseline and candidate were produced on clean commit
  `cb61b52affd5ecdb4095312087400fb482d8301b`, the PR #22 merge commit.
- Both runs used KuaiRand-Pure development data hash
  `69e5a6f656356832f7e1fa6a9774bc404030f32874e18e57e0f38b6a309a1002`,
  seed `0`, maximum date `20220428`, and zero test rows.
- Baseline prediction SHA-256:
  `56d317930cd4bacb0fae0f6c6798834a440bc2a6c5a991a50c1ce81f406b86dc`.
- Candidate prediction SHA-256:
  `d137ce7d482d2cb8a2042d59831fa1fd1b1de50abd93bef288c189e11e05c0e3`.
- Both completed artifact packages passed `tools.audit_run` byte, path,
  config, data, protected-hash, clean-worktree, and command auditing.
- Both predictions passed the exact 124,909-row valid prediction contract.
- E evaluated the immutable predictions with protected
  `starter/evaluate.py` hash
  `ecfde28392eb14fec4f488083251df50624e1af2b86278b962daecfb42d195de`.

## Metrics

| Run | GAUC | nDCG@5 | Primary |
| --- | ---: | ---: | ---: |
| Baseline FM | 0.6671326321610643 | 0.5358048805448538 | 0.601468756352959 |
| Same-user BPR FM | 0.6705350761953585 | 0.5372069380698954 | 0.603871007132627 |

Each primary value is the arithmetic mean of GAUC and nDCG@5. Both runs cover
124,909 valid rows and 22,377 users.

## Human override disclosure

At the time of execution, `coordination/current_state.json` had not yet been
updated after PR #22 and still described the superseded PR #18 artifact gap.
The human repository operator explicitly instructed E to independently review
the merged changes and proceed without waiting for an additional A review.
That instruction is counted as one manual intervention in the committed E
metrics records. E did not edit A-owned governance state or create a final
approval.

## Evidence

- `reports/evaluation/exp_001_baseline_metrics.json`
- `reports/evaluation/exp_001_candidate_metrics.json`
- Local Git-ignored baseline package:
  `artifacts/exp_001_baseline/run_manifest.json`
- Local Git-ignored candidate package:
  `artifacts/exp_001_candidate/run_manifest.json`
- Local Git-ignored development snapshot: `data/dev/dataset_manifest.json`

Large data, predictions, checkpoints, and generated run artifacts remain
excluded from Git.

## Remaining release work

- A-owned coordination state still needs reconciliation with the merged PR #22
  and this E result.
- No final approval exists.
- Test remains denied and was not accessed.
- A separate human-approved final release workflow is required before any test
  operation.
