# exp_001 fresh valid cycle decision — A

STATUS=VALID_IMPROVEMENT_ACCEPTED
ROLE=A
EXPERIMENT_ID=exp_001
PRODUCING_COMMIT_SHA=44fd36aa9b35b7fc9c01389e6dd453e972f16635
EVIDENCE_MAIN_SHA=2dc456539aa4e75665434b35ba86d23bfd1f0fa1
BASELINE_PRIMARY=0.601468756352959
CANDIDATE_PRIMARY=0.603871007132627
PRIMARY_DELTA=0.0024022507796679
MINIMUM_IMPROVEMENT=0.002
STRICT_IMPROVEMENT_RULE=PASS
CANDIDATE_THRESHOLD=0.6036
CANDIDATE_THRESHOLD_CHECK=PASS
CHAMPION_CONFIG=configs/candidates/bpr_fm.json
FORMAL_RUN_AUTHORIZATION_CONSUMED=true
AUTHORIZED_RUNS_REMAINING=0
PR25_EVIDENCE_ACCEPTED=false
FRESH_RESULT_ACCEPTED_WITH_PROCESS_INCIDENT_DISCLOSURE=true
FINAL_APPROVAL_CREATED=false
test_access=false
NEXT_RECEIVER=A_FOR_NEXT_EXPERIMENT_OR_RELEASE_DECISION

## Decision

A accepts the fresh same-user BPR candidate as the validation champion for
`exp_001`. The candidate improves primary over the same-commit baseline by
`0.0024022507796679`, strictly greater than the approved `0.002` rule, and its
primary `0.603871007132627` exceeds the absolute `0.6036` threshold.

This decision uses only the fresh packages produced on clean commit
`44fd36aa9b35b7fc9c01389e6dd453e972f16635` and the isolated E evaluation
merged in PR #40. The one authorized formal baseline/candidate pair is now
consumed. No additional formal run is authorized.

## Evidence accepted

- B handoff PR #39 merged as
  `cb61753bc4d23ee1207c37ec6e3dfb3c06e2008c` after 4/4 checks.
- E evaluation PR #40 merged as
  `2dc456539aa4e75665434b35ba86d23bfd1f0fa1` after 4/4 checks.
- Both packages bind the same producing commit, development-data hash,
  unchanged FM features, seed 0, and full budget with `max_batches=null`.
- Both run-manifest contracts, artifact-byte audits, and 124,909-row prediction
  contracts passed.
- The isolated E evaluator used the protected official evaluator on valid only,
  verified primary arithmetic, and confirmed both prediction hashes unchanged.

## Process incident disposition

After both B runs and immutable hashes were already complete, the coordinating
root session accidentally opened the quarantined PR #25 metrics while looking
for an output schema. The session was immediately excluded from E scoring. A
new E sub-agent with no inherited conversation context was explicitly forbidden
from reading PR #25 and independently reproduced the fresh valid metrics.

The repository owner was informed of the exact incident and explicitly
confirmed A's recommendation to accept the fresh result with permanent
disclosure and no rerun. A records the incident as contained and non-causal:
it could not affect completed training or frozen predictions, and the isolated
E evaluation did not use the old evidence. PR #25 remains permanently
quarantined and is not accepted for selection, thresholds, or reporting.

## Remaining boundary

This is a valid-only research decision, not a final release approval. No final
approval was created, no test data was accessed, and test remains blocked until
a new exact human approval is bound to a clean frozen release commit.
