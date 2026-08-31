# exp_003 formal valid-only run instruction blocker — B

STATUS=BLOCKED
ROLE=B
PHASE=FORMAL_VALID_ONLY_RUN
EXPERIMENT_ID=exp_003
OBSERVED_AT_UTC=2026-08-31T13:28:10Z
APPROVED_AGAINST_COMMIT_SHA=58962df016da5808236b73d135a7abdd1d3fe879
REVIEWED_MAIN_SHA=863e823463b306d191e5ccc8bcf0790c8ed102cb
REAL_VALID_GATE_STATUS=ALLOWED_EXACTLY_ONE_FULL_BUDGET_VALID_ONLY_PAIR
FORMAL_GATE_CONSUMED=false
DATASET_MANIFEST_ACCESSED=false
REAL_DATA_ACCESSED=false
REAL_DATA_TRAINING_PERFORMED=false
GENERATED_ARTIFACTS_CREATED=false
FORMAL_METRICS_PRODUCED=false
PR25_EVIDENCE_USED=false
FINAL_APPROVAL_CREATED=false
test_access=false
NEXT_RECEIVER=A

## Blocker

The merged repository state assigns B exactly one full-budget, valid-only
baseline/candidate pair for exp_003. The active role-step instruction separately
and explicitly prohibits real-data training and formal validation metrics. B cannot
satisfy both constraints by executing the pair, and the already consumed one-batch
synthetic gate does not authorize another synthetic run or a substitute package.

B therefore did not open or hash the private development dataset or its manifest,
invoke the experiment runner, train either model, create a prediction or checkpoint,
evaluate validation output, or consume the formal pair. No large artifact exists for
handoff. PR #25 evidence was neither read nor used.

A must route a fresh B role step whose instruction expressly permits the already
recorded real-development-data, full-budget, valid-only baseline/candidate pair.
The exact gate remains unconsumed. Hidden-test access and final release remain
forbidden.

## Repository verification

Every Python command used
`/Users/pengrenzhong/Documents/GitHub/BOB-AGENT/.venv/bin/python`.

- Required unit suite: PASS, 177/177 tests.
- Repository contracts: PASS, 53 JSON files plus JSONL/TOML validated.
- Protected-file checks: PASS, all seven pinned files matched in both verifiers.
- Prediction-contract tests: PASS, 9/9 synthetic tests.
- Exp_003 experiment-spec contract: PASS.

These checks used repository fixtures only. They produced no formal metric, private
run package, prediction, checkpoint, credential, or committed generated artifact.
