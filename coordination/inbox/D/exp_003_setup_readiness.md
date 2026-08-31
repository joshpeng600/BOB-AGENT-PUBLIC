# exp_003 config-only setup readiness

STATUS=READY_FOR_A_INTEGRATION_REVIEW
AUTHOR_ROLE=D
EXPERIMENT_ID=exp_003
APPROVED_AGAINST_COMMIT_SHA=4b0bea90b688cc064ddb8f08e572acd448826c87
BASE_MAIN_SHA=1631398bad0e57671f8425c033b545c9cdae64fb
IMPLEMENTATION_COMMIT_SHA=76c7f2ec2ae3867ed33b66f2209090edded0b60a
CANDIDATE_CONFIG=configs/candidates/bpr_fm_dim32.json
CANDIDATE_CONFIG_SHA256=e185476e13a0976ac227e84c486bd798ce0e6ae8753f98ead4d48a24036ac1a2
BASELINE_CONFIG=configs/approved/exp_001.json
BASELINE_CONFIG_SHA256=5221e0efdaace6f0aaa196da3cfdf51a4fdb154cf3043cd6b71252a62cf0823c
EXPERIMENT_SPEC=experiments/exp_003.json
EXPERIMENT_SPEC_SHA256=79c0e54f962c84213c0150474894ff695d5d6acfed85aa2955abb173b425f20c
SINGLE_SCIENTIFIC_CHANGE=model.embedding_dim:16->32
MODEL_FAMILY_UNCHANGED=true
OBJECTIVE_UNCHANGED=true
SAMPLING_UNCHANGED=true
FEATURES_UNCHANGED=true
TRAINING_BUDGET_UNCHANGED=true
SEED=0
DATA_MODE=train_valid_only
MAXIMUM_DEVELOPMENT_DATE=20220428
CONFIG_DIFF_CHECK=PASS
REPOSITORY_CONTRACTS=PASS
PROTECTED_HASHES=PASS
UNIT_TESTS=unittest 175/175 passed
PREDICTION_CONTRACT_TESTS=9/9 passed
REAL_DATA_ACCESSED=false
REAL_DATA_TRAINING_PERFORMED=false
FORMAL_METRICS_PRODUCED=false
REAL_VALID_RUN_ALLOWED=false
PR25_EVIDENCE_USED=false
FINAL_APPROVAL_CREATED=false
test_access=false
BLOCKERS=none
NEXT_RECEIVER=A

## Config-only implementation

The candidate is a config-only derivative of the accepted exp_001 champion.
A recursive structured comparison over the scientific configuration reported
exactly one difference:

`model.embedding_dim: 16 -> 32`

The factorization-machine family, learning rate, L2 value, same-user BPR
objective and formula, one-negative sampling, eligibility rules, training seed,
batch size, epoch and patience budgets, `max_batches`, allowed splits,
development-date boundary, and validation-only evaluation split are unchanged.
No model or training source, feature, runner, evaluator, protected file, or
`starter/` file was modified.

## Clean implementation-commit checks

Checks were run with the required repository runtime on the clean implementation
commit `76c7f2ec2ae3867ed33b66f2209090edded0b60a`:

- Structured scientific config diff: PASS, exactly
  `model.embedding_dim: 16 -> 32`.
- `python -m unittest discover -s tests -v`: PASS, 175/175 tests.
- `python scripts/check_repository_contracts.py`: PASS, 53 JSON files plus
  JSONL/TOML validated.
- `python scripts/check_protected_files.py`: PASS, all seven protected files
  matched their pinned hashes.
- `python scripts/check_prediction_contract.py`: PASS, 9/9 tests.
- `git diff --check`: PASS.
- `git diff -- starter/`: PASS, empty.
- `git status --porcelain`: PASS, empty.

These checks establish configuration and repository-contract readiness only.
The private development dataset was not accessed because this D step was not
data-dependent. No training, predictions, checkpoints, generated artifacts,
formal validation metrics, candidate decision, test access, PR #25 evidence,
or final approval was produced. A must review and merge this PR before it can
serve as a prerequisite for later roles.
