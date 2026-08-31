# exp_003 formal-run blocker

STATUS=BLOCKED
ROLE=B
PHASE=FORMAL_VALID_ONLY_RUN
EXPERIMENT_ID=exp_003
APPROVED_AGAINST_COMMIT_SHA=58962df016da5808236b73d135a7abdd1d3fe879
REPOSITORY_HEAD_SHA=ceb91cb3b1b1f0be8d54b8e83d46c7afc1b96b3a
REAL_VALID_GATE_STATUS=ALLOWED_EXACTLY_ONE_VALID_ONLY_PAIR
REAL_DATA_ACCESSED=false
REAL_DATA_TRAINING_PERFORMED=false
FORMAL_METRICS_PRODUCED=false
FORMAL_GATE_CONSUMED=false
DATASET_MANIFEST_ACCESSED=false
GENERATED_ARTIFACTS_CREATED=false
PR25_EVIDENCE_USED=false
FINAL_APPROVAL_CREATED=false
test_access=false
NEXT_RECEIVER=A

## Blocker

The current repository state assigns B exactly one full-budget, real-development-data,
valid-only baseline/candidate pair. The active task instruction for this role step
simultaneously prohibits real-data training and formal validation metrics. There is no
remaining synthetic run authorization: the one-batch synthetic gate was already
consumed and merged in PR #17.

B therefore did not invoke the formal runner, access the private development dataset,
hash or inspect its manifest, train either model, create predictions or checkpoints,
evaluate validation output, or consume the one authorized formal pair. Executing a
partial, synthetic, or invented substitute would violate the exact gate and would not
produce acceptable evidence for E.

A must obtain or record a role-step instruction that permits the already gated
real-development-data, valid-only run before routing the action back to B. The existing
formal gate remains unconsumed. Test access and final release remain forbidden.

## Repository checks

Every Python command used `D:\Program Files\python.exe`, as required for this role
step.

- `-m unittest discover -s tests -v`: **FAIL**; 175 tests ran, with 1 failure,
  4 platform skips, and 170 passes. The existing
  `test_codex_command_uses_reviewable_sandbox` assertion expected `/repo/.git`, while
  the Windows runtime rendered the mocked path as `\repo\.git`. B does not claim the
  required unit suite passed and did not alter the campaign runner or its test to mask
  this result.
- `scripts/check_repository_contracts.py`: PASS; 53 JSON files plus JSONL/TOML
  validated.
- `scripts/check_protected_files.py`: PASS; all seven pinned starter files matched.
- `scripts/check_prediction_contract.py`: PASS; 9/9 synthetic contract tests.
- `tools/validate_contract.py --type experiment-spec --path experiments/exp_003.json`:
  PASS.

This file is blocker evidence only. It contains no model-quality claim, run package,
prediction, checkpoint, credential, generated artifact, or formal metric.
