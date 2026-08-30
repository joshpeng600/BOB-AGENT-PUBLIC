# exp_002 delegated config-only setup readiness

STATUS=READY_FOR_INDEPENDENT_B_E_REVIEW
AUTHOR_ROLE=A
EXECUTED_ON_BEHALF_OF_ROLE=D
MANUAL_INTERVENTION=governance/manual_interventions.jsonl
EXPERIMENT_ID=exp_002
BASE_MAIN_SHA=c5280a1b434f314420e7add028a67414166803f6
IMPLEMENTATION_COMMIT_SHA=77e577675b9d6a04a56321ee0aab0d437d98dacf
CANDIDATE_CONFIG=configs/candidates/bpr_fm_neg2.json
BASELINE_CONFIG=configs/approved/exp_001.json
SINGLE_SCIENTIFIC_CHANGE=objective.negatives_per_positive:1->2
MODEL_UNCHANGED=true
FEATURES_UNCHANGED=true
TRAINING_BUDGET_UNCHANGED=true
SEED=0
DATA_MODE=train_valid_only
MAXIMUM_DEVELOPMENT_DATE=20220428
CONFIG_DIFF_CHECK=PASS
INDEPENDENT_D_REVIEW_PERFORMED=false
B_REVIEW_REQUIRED=true
E_REVIEW_REQUIRED=true
REPOSITORY_CONTRACTS=PASS
PROTECTED_HASHES=PASS
UNIT_TESTS=pytest 121 passed; unittest 121/121 passed
REAL_DATA_TRAINING_PERFORMED=false
FORMAL_METRICS_PRODUCED=false
REAL_VALID_RUN_ALLOWED=false
PR25_EVIDENCE_USED=false
test_access=false
BLOCKERS=none
NEXT_RECEIVER=B

## Delegation disclosure

This readiness record was authored and executed by role A under the one-time
human authorization appended to `governance/manual_interventions.jsonl`. It
does not claim authorship or independent review by role D. The authorization
is limited to this config-only delivery and does not grant A standing D
ownership. Independent B and E contract verification remains required.

## Config-only implementation

The candidate inherits the accepted exp_001 champion's model, objective,
training budget, seed, development-data boundary, allowed splits, and valid
evaluation split. A recursive structured JSON comparison over the scientific
configuration reported exactly one difference:

`objective.negatives_per_positive: 1 -> 2`

No model, feature, training source, runner, validator, evaluator, protected
file, or `starter/` file was modified. No result, expected formal metric,
KEEP/IMPROVED decision, or final approval is claimed.

## Clean implementation-commit checks

Checks were run in a detached clean worktree at
`77e577675b9d6a04a56321ee0aab0d437d98dacf`:

- `python -m pytest -q`: PASS, 121 passed in 0.59s.
- `python -m unittest discover -s tests -v`: PASS, 121/121 passed in 0.429s.
- `python scripts/check_repository_contracts.py`: PASS, 40 JSON files plus JSONL/TOML validated.
- `python scripts/check_protected_files.py`: PASS, all seven protected files matched.
- `python scripts/check_prediction_contract.py`: PASS, 9/9 tests.
- `git diff --check`: PASS.
- `git diff -- starter/`: PASS, empty.
- `git status --porcelain`: PASS, empty.

These are repository and interface checks only. Real-data training, formal
metric production, PR #25 evidence use, and test access did not occur.
