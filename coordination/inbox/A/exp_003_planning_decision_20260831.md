# exp_003 planning decision

STATUS=IMPLEMENTATION_SETUP_APPROVED
ROLE=A
EXPERIMENT_ID=exp_003
BASE_MAIN_SHA=4b0bea90b688cc064ddb8f08e572acd448826c87
CURRENT_CHAMPION=exp_001
CURRENT_CHAMPION_PRIMARY=0.603871007132627
STRICT_MINIMUM_IMPROVEMENT=0.002
CANDIDATE_PRIMARY_MUST_BE_GREATER_THAN=0.605871007132627
SINGLE_SCIENTIFIC_CHANGE=model.embedding_dim:16->32
DATASET_MANIFEST_SHA256=69e5a6f656356832f7e1fa6a9774bc404030f32874e18e57e0f38b6a309a1002
REAL_VALID_RUN_ALLOWED=false
FORMAL_METRICS_PRODUCED=false
PR25_EVIDENCE_USED=false
FINAL_APPROVAL_CREATED=false
test_access=false

## Decision

The retained exp_001 same-user BPR champion is the approved baseline. Exp_003
doubles only `model.embedding_dim` from 16 to 32. The objective, negative
sampling, features, seed, evaluator, batch size, epoch and patience budgets,
and all data boundaries remain fixed.

This isolates a capacity hypothesis after exp_002 showed that additional
negative exposure did not improve validation. Failure would rule out simple FM
capacity scaling at the fixed objective and budget.

## Prerequisites reviewed

- Exp_002 is completed and rejected on merged independent evidence; exp_001
  remains the champion.
- The policy count is one consecutive non-improvement, below the stop limit of
  three.
- The bounded exp_003-exp_005 train/valid-only campaign is active.
- The exact private development manifest exists and its SHA-256 matches the
  authorized frozen hash. No dataset content was copied into Git.
- The working base is clean `origin/main` at the full SHA recorded above.

## Stage order

1. C performs a read-only data/leakage and memory-feasibility review.
2. D adds the config-only candidate and proves that only the embedding dimension
   changed.
3. After the C and D evidence is merged, B performs clean-commit contract
   preflight and at most one one-batch synthetic smoke.
4. E independently pre-reviews the merged setup without scoring.
5. A reviews every merged C/D/B/E prerequisite and only then may separately
   decide whether to authorize one full-budget valid-only pair.

No real-data training, formal validation metrics, test access, or final approval
is authorized by this planning record.
