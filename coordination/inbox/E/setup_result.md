# E setup safety audit result

STATUS=SETUP_READY
BASE_MAIN_SHA=c6703454c2a0030c7bdb0ee6bf2af5a3019ca497
BRANCH=E-Part

This is a setup-readiness result only. It is not an experiment ACCEPT/REJECT
decision and contains no formal validation or test metrics.

## Protected hash check

- `python tools/verify_protected_files.py --manifest protected_manifest.json --repo-root .`
  returned `PROTECTED_FILES=PASS`.
- `protected_manifest.json` and `governance/protected_files.json` agree for the
  four protected evaluation/data/submission/baseline-score files.
- `starter/` was read only and was not modified.
- Protected evaluation continues to use canonical LF hashing across platforms;
  non-line-ending content changes remain rejected.

## Prediction contract check

- Exact header `row_id,user_id,video_id,score` is enforced.
- `row_id` must use the canonical zero-based contiguous representation; values
  such as `00` and `+0` are rejected.
- Prediction row count and per-row `user_id`/`video_id` must exactly match the
  official valid rows.
- Repeated `(user_id, video_id)` rows are preserved and accepted when their
  `row_id` values are distinct; no deduplication occurs.
- Scores must parse as finite numbers; NaN and positive/negative infinity are
  rejected.
- The evaluator reads prediction scores without rewriting them, hashes the
  immutable prediction before and after evaluation, and refuses an output path
  that would overwrite the prediction.
- All checks used synthetic valid fixtures only.

## Valid-only evaluation gate check

- Ordinary `tools/validate_predictions.py` access is restricted to
  `split=valid` and rejects other splits before data access.
- `tools/safe_evaluate.py` allows ordinary valid evaluation only; test requires
  the separate final-approval verifier.
- Evaluation is denied before scoring when the worktree is dirty.
- The evaluation commit is frozen at start and must remain the same, with a
  clean worktree, through evidence creation.
- GAUC, nDCG@5, and primary are obtained only from protected
  `starter/evaluate.py`; the gate verifies that primary is the arithmetic mean
  of GAUC and nDCG@5.
- Synthetic evidence records `evaluator_role=E`, `worktree_clean=true`, and
  `test_access=false`.

## Test rejection path check

- A `split=test` request without `--approval` is rejected before prediction or
  data access with `Normal mode only permits valid; test requires --approval`.
- Run-manifest command history containing test scoring is rejected.
- No test label, test metric, or test prediction was read or produced during
  this setup audit.

## Run manifest audit result

- A complete `run_manifest` schema is required; partial manifests are rejected.
- `experiment_id` and a full lowercase 40-character `commit_sha` are required.
- `commit_sha` must match the exact evaluation-code HEAD.
- Both recorded `worktree_clean=true` and an actually clean worktree are
  required.
- `executor_role=B` is required.
- `config_hash`, `data_hash`, `prediction_hash`, and `checkpoint_hash` must be
  present as lowercase SHA-256 values.
- `config_hash` must bind the recorded config and `data.hash` must equal
  `data_hash`.
- Protected hashes must exactly match `protected_manifest.json`.
- `dev_max_date` must be at most `20220428`.
- Recorded commands must not contain test scoring.
- Legacy aliases `exp_id`, `base_commit`, `commit`, and `frozen_commit` are
  rejected recursively.
- Completed formal metrics contracts require `evaluator_role=E`, `split=valid`,
  finite GAUC/nDCG@5/primary, and arithmetic-mean primary through
  `tools/validate_contract.py`.

## Final approval gate check

- Test access is denied without a complete final-approval contract.
- Approval must identify a human; AI names and template placeholders are
  rejected.
- Approval must bind the full current commit SHA, an actually clean worktree,
  and the current protected hashes.
- Legacy commit aliases are rejected.
- No final approval was created, modified, or approved in this setup task.

## Modified files

- `tools/audit_run.py`
- `tools/final_approval.py`
- `tools/safe_evaluate.py`
- `tools/validate_predictions.py`
- `tests/test_audit.py`
- `tests/test_predictions.py`
- `tests/test_safe_evaluate.py`
- `coordination/inbox/E/setup_result.md`

No files under `starter/`, `src/models/`, `src/training/`, `src/data/`,
`configs/`, `governance/`, or `tools/run_experiment.py` were modified.

## Test commands and results

The host initially had no `python` command alias. The bundled Python runtime
(Python 3 with NumPy) was therefore exposed as `python` through `PATH`; no
dependency was installed and no repository environment was changed.

- `python -m unittest tests.test_safe_evaluate -v` — PASS, 4 tests.
- `python -m unittest tests.test_audit -v` — PASS, 14 tests.
- `python -m unittest tests.test_predictions -v` — PASS, 7 tests.
- `python -m unittest tests.test_submission -v` — PASS, 9 tests.
- `python -m unittest tests.test_project_security -v` — PASS, 5 tests.
- `python -m unittest discover -s tests -v` — PASS, 76 tests.
- `python tools/verify_protected_files.py --manifest protected_manifest.json --repo-root .`
  — PASS (`PROTECTED_FILES=PASS`).

## Not yet verified

- No immutable B-produced `valid_predictions.csv` exists for formal E review.
- No formal B run manifest, prediction hash, checkpoint hash, or artifact set
  was audited; only synthetic contract fixtures were checked.
- No official valid dataset was scored and no formal `metrics.json` was
  produced.
- No final human approval exists or was requested.
- Test access and release approval remain outside this setup task.

IMMUTABLE_B_OUTPUT_AVAILABLE=false
FORMAL_EVALUATION_PERFORMED=false
test_access=false
