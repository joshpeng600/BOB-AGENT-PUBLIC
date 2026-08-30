# E setup evidence correction

STATUS=SETUP_READY_WITH_GOVERNANCE_REVIEW_PENDING
BASE_MAIN_SHA=6fa3d227e4875161a70879db386dd2fef734b405
ACTUAL_SYNCED_MAIN_SHA=5394f261567a0cd7e0c1ebe3bb6a700c7e97dee3
ROLE=E
BRANCH=E-Part
PR_10_MERGED=true
COMBINED_TEST_SUITE_PASS=true
COMBINED_TEST_COUNT=77
PROTECTED_FILES=PASS
EXPERIMENT_CONTRACT=PASS
IMMUTABLE_B_OUTPUT_AVAILABLE=false
FORMAL_EVALUATION_PERFORMED=false
FORMAL_METRICS_PRODUCED=false
FINAL_APPROVAL_CREATED=false
test_access=false
CROSS_ROLE_REVIEW_PENDING=true

This is a setup evidence correction only. It is not a cycle evaluation, does
not contain an experiment ACCEPT/REJECT decision, and does not contain formal
validation or test metrics. All executable checks used repository synthetic
fixtures only.

## Base and merge provenance

- PR #10 is merged as
  `6fa3d227e4875161a70879db386dd2fef734b405`; this is the required setup
  evidence baseline recorded by `BASE_MAIN_SHA`.
- Before this revalidation, `E-Part` was switched normally and merged with
  `origin/main` without rebase, force-push, or history rewriting.
- At synchronization time, `origin/main` had advanced to
  `5394f261567a0cd7e0c1ebe3bb6a700c7e97dee3` through merged PR #11. That
  descendant adds `coordination/inbox/C/setup_result.md` only, so the actual
  synchronized main SHA is recorded separately rather than misrepresented as
  the PR #10 merge SHA.
- C PR #9 is merged as `66f9577b65223003eaf1bff51551116828db19fc`.
  Its current `tests/test_build_dev_dataset.py` test coverage is present in the
  combined 77-test suite on the synchronized main.

## PR #10 changed files and ownership review

PR #10 changed exactly these files relative to its first parent:

- `coordination/inbox/E/setup_result.md`
- `tests/test_audit.py`
- `tests/test_predictions.py`
- `tests/test_safe_evaluate.py`
- `tools/audit_run.py`
- `tools/final_approval.py`
- `tools/safe_evaluate.py`
- `tools/validate_predictions.py`

E-owned evaluation, audit evidence, and release-gate files:

- `coordination/inbox/E/setup_result.md`
- `tools/audit_run.py`
- `tools/final_approval.py`
- `tools/safe_evaluate.py`

B-owned validator and test files changed by PR #10:

- `tools/validate_predictions.py`
- `tests/test_audit.py`
- `tests/test_predictions.py`
- `tests/test_safe_evaluate.py`

`AGENTS.md` assigns validators and all `tests/` to B and requires an A-recorded
exception for cross-role changes. The current
`governance/manual_interventions.jsonl` contains no corresponding manual
intervention exception for PR #10 or these B-owned changes. This revalidation
does not roll back the safety checks, modify governance, or alter A-owned
`coordination/current_state.json`.

No functional error was found in the current evaluator, validator, audit, or
release-gate behavior by the specified synthetic checks. The outstanding issue
is ownership and human governance review, not a presently observed functional
failure.

Required follow-up:

- A must review the cross-role history and decide whether to record an explicit
  manual-intervention exception or require an ownership-correct follow-up.
- B must manually review and accept or reject the PR #10 validator/test changes
  in its owned area.
- E must not resolve either governance decision on its own.

## Protected files

- `python tools/verify_protected_files.py --manifest protected_manifest.json --repo-root .`
  returned `PROTECTED_FILES=PASS`.
- Protected evaluator/data/submission/baseline-score hashes match
  `protected_manifest.json`.
- No protected or `starter/` file was modified in this task.

## Prediction contract

- The exact header `row_id,user_id,video_id,score` is required.
- `row_id` is zero-based and contiguous, and the row count must exactly match
  official valid rows.
- `user_id` and `video_id` must match official valid rows in the same order.
- Duplicate user/video pairs remain distinct rows and are not deduplicated.
- Scores must be finite numeric values; NaN and Inf are rejected.
- Evaluation hashes the immutable prediction before and after use and does not
  modify it.
- Only synthetic valid fixtures were checked; no B prediction was available.

## Valid-only and test-denial gates

- Ordinary prediction validation and evaluation permit `split=valid` only.
- Test requires the separate final-approval path and is denied without it
  before prediction or data access.
- Setup/cycle ordinary paths do not emit test metrics.
- GAUC, nDCG@5, and primary come from protected `starter/evaluate.py`; the gate
  verifies that primary is the arithmetic mean of GAUC and nDCG@5.
- E did not train a model, repair B's runner, adjust a prediction, access test,
  or create a final approval.

## Run-manifest and final-gate audit

- A completed run manifest requires a full 40-character `commit_sha`, an
  actually clean worktree, and `worktree_clean=true`.
- The manifest commit must be the evaluation-code commit; `executor_role=B` is
  required, while formal metrics require `evaluator_role=E`.
- `config_hash`, `data_hash`, `prediction_hash`, and `checkpoint_hash` must be
  present and bind their recorded artifacts; protected hashes must match.
- `dev_max_date` must not exceed `20220428`, and commands must not contain test
  scoring.
- Legacy aliases `exp_id`, `base_commit`, `commit`, and `frozen_commit` are
  rejected recursively.
- Test access requires a human approval bound to the full current clean commit
  and current protected hashes. No approval was created or approved here.

## Commands and results

The bundled Python runtime was exposed as `python` through `PATH`; no
dependency or repository environment was changed.

- `python -m unittest tests.test_safe_evaluate -v` — PASS (4 tests).
- `python -m unittest tests.test_audit -v` — PASS (14 tests).
- `python -m unittest tests.test_predictions -v` — PASS (7 tests).
- `python -m unittest tests.test_submission -v` — PASS (9 tests).
- `python -m unittest tests.test_project_security -v` — PASS (5 tests).
- `python -m unittest discover -s tests -v` — PASS (77 tests).
- `python tools/verify_protected_files.py --manifest protected_manifest.json --repo-root .`
  — PASS (`PROTECTED_FILES=PASS`).
- `python tools/validate_contract.py --type experiment-spec --path experiments/exp_001.json`
  — PASS (`CONTRACT=PASS`).

## Real B artifacts not yet verified

- No immutable B-produced `valid_predictions.csv` exists for formal E review.
- No B-produced completed `run_manifest.json`, checkpoint, resolved config,
  development-data manifest, or their artifact hashes were audited.
- No official valid dataset was scored and no formal `metrics.json` was
  produced.

## Immutable cycle handoff required by E

Before a cycle evaluation, E must receive from B, all bound to the same full,
frozen, clean `commit_sha`:

- immutable `valid_predictions.csv` with its `prediction_hash`;
- completed `run_manifest.json` with `executor_role=B`;
- immutable model checkpoint with `checkpoint_hash`;
- resolved approved config plus `config_hash`;
- development-data manifest/evidence plus `data_hash` and
  `dev_max_date <= 20220428`;
- protected hashes and an artifact list containing paths and SHA-256 values;
- the exact run commands, environment, seed, start/finish times, and run ID.

Only after those immutable artifacts exist may E audit and independently score
valid. Test and final approval remain outside this setup task.
