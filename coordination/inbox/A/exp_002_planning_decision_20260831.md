# exp_002 planning decision

STATUS=IMPLEMENTATION_SETUP_APPROVED
ROLE=A
EXPERIMENT_ID=exp_002
BASE_MAIN_SHA=8eb5bad5d1ce24ee8d68451dddd45a10414119c5
CURRENT_CHAMPION=exp_001
CURRENT_CHAMPION_PRIMARY=0.603871007132627
STRICT_MINIMUM_IMPROVEMENT=0.002
CANDIDATE_PRIMARY_MUST_BE_GREATER_THAN=0.605871007132627
SINGLE_SCIENTIFIC_CHANGE=objective.negatives_per_positive:1->2
REAL_VALID_RUN_ALLOWED=false
FORMAL_METRICS_PRODUCED=false
FINAL_APPROVAL_CREATED=false
test_access=false

## Decision

The accepted exp_001 Same-user BPR candidate is promoted to an approved exp_002 baseline configuration. D's read-only design review recommended increasing `negatives_per_positive` from 1 to 2 as the single scientific change because it increases negative exposure while preserving the model, features, objective family, seed, evaluator, and nominal training budget.

Alternatives considered were increasing the embedding dimension and increasing the learning rate. Both introduce broader capacity or optimization risk, so they were not selected for this round.

## Required infrastructure repair before any formal run

The current B-owned run contract validator hardcodes the baseline objective to pointwise BCE. That is incompatible with replaying the accepted BPR champion as the exp_002 baseline. B must generalize this check so the baseline objective is derived from the approved baseline config bound by the experiment spec, while preserving all existing route, identity, byte-hash, and resolved-config protections.

This is a synthetic/contract repair only. It does not authorize real data use, formal metrics, or test access.

## Stage order

1. B repairs and tests baseline route semantics using synthetic fixtures only.
2. D adds the config-only candidate with `negatives_per_positive=2`.
3. C reports unchanged-data feasibility and estimates the doubled sampling work.
4. E independently pre-reviews the integrated routes and safety gates without scoring.
5. A reviews merged evidence and separately decides whether to authorize exactly one fresh full-budget valid-only baseline/candidate pair.

No formal run authorization is active in this planning decision.
