# exp_002 cycle decision — A

STATUS=VALID_IMPROVEMENT_REJECTED
ROLE=A
EXPERIMENT_ID=exp_002
PRODUCING_COMMIT_SHA=fced9a79ae3e06af69e06d319ee316e77fcce98a
EVIDENCE_MAIN_SHA=d843c2b93382c21baf99b7c9105e910621e8a299
BASELINE_PRIMARY=0.603871007132627
CANDIDATE_PRIMARY=0.6032604702292279
PRIMARY_DELTA=-0.0006105369033990726
MINIMUM_IMPROVEMENT=0.002
STRICT_IMPROVEMENT_RULE=FAIL
CANDIDATE_THRESHOLD=0.605871007132627
CANDIDATE_THRESHOLD_CHECK=FAIL
RETAINED_CHAMPION_EXPERIMENT_ID=exp_001
RETAINED_CHAMPION_CONFIG=configs/approved/exp_001.json
FORMAL_RUN_AUTHORIZATION_CONSUMED=true
AUTHORIZED_RUNS_REMAINING=0
PR25_EVIDENCE_USED=false
FINAL_APPROVAL_CREATED=false
test_access=false
NEXT_RECEIVER=A_FOR_NEXT_EXPERIMENT_OR_RELEASE_DECISION

## Decision

A rejects the exp_002 two-negative candidate and retains exp_001 as the
validation champion. The independently evaluated candidate primary is lower
than the same-commit baseline by `0.0006105369033990726` and does not exceed
the strict acceptance threshold `0.605871007132627`.

The one authorized exp_002 formal baseline/candidate pair is consumed. No
additional exp_002 run is authorized. A future cycle must create a new
single-variable experiment from the retained exp_001 champion.

## Evidence accepted

- B produced both packages on clean commit
  `fced9a79ae3e06af69e06d319ee316e77fcce98a`, with identical data, features,
  seed 0, and full budget (`max_batches=null`).
- E PR #52 merged as `d843c2b93382c21baf99b7c9105e910621e8a299`
  after all four required checks passed.
- E independently verified both artifact and prediction contracts, evaluated
  valid only with the protected evaluator, and confirmed predictions remained
  byte-identical after scoring.
- E did not use runner self-reported metrics or quarantined PR #25 evidence.

## Remaining boundary

This is a valid-only research decision. No final approval was created, test was
not accessed, and final release remains blocked behind a separate exact human
approval bound to a clean frozen release commit.
