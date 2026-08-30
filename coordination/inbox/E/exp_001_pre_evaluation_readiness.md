# exp_001 pre-evaluation readiness — E

STATUS=BLOCKED
ROLE=E
MAIN_SHA=5dd9460d5904b3bf69627b005ebe4ebeb67bafe9
B_READINESS_REVIEWED=true
B_READINESS_MERGED=true
B_READINESS_PR_NUMBER=15
B_READINESS_PR_HEAD_SHA=2ff640d3b695d8b6e3a4ee05ea2b07038e5ac43c
B_IMPLEMENTATION_COMMIT_SHA=5ab859b135be02db07d03a24a1827a81ecac656d
DATA_MANIFEST_SHA256=69e5a6f656356832f7e1fa6a9774bc404030f32874e18e57e0f38b6a309a1002
C_DATA_EVIDENCE_REVIEWED=true
D_INTERFACE_EVIDENCE_REVIEWED=true
EXPECTED_ARTIFACT_CONTRACT=FAIL
PREDICTION_CONTRACT=PASS
PROTECTED_HASHES=PASS
REPOSITORY_CONTRACTS=PASS
REAL_VALID_RUN_ALLOWED=false
IMMUTABLE_B_OUTPUT_AVAILABLE=false
FORMAL_EVALUATION_PERFORMED=false
FORMAL_METRICS_PRODUCED=false
FINAL_APPROVAL_CREATED=false
TEST_ACCESS=false
BLOCKERS=The completed-run artifact contract does not yet require or emit a SHA-256 artifact entry for resolved_config.json, and the current validator/auditor does not require the complete formal package or verify each declared artifact against its file bytes; coordination/current_state.json also still leaves REAL_VALID_RUN_ALLOWED pending.
NEXT_RECEIVER=B

## Scope

This is an E-owned contract pre-review only. No model training, real validation
evaluation, metric computation, prediction repair, final approval, or test
access was performed. Synthetic smoke evidence was not treated as an immutable
formal prediction package.

## Merge and B readiness review

- The checked-out `origin/main` is
  `5dd9460d5904b3bf69627b005ebe4ebeb67bafe9`.
- That commit is the Git merge commit whose message records PR #15 from
  `B-Part`; its second parent, the merged B PR head, is
  `2ff640d3b695d8b6e3a4ee05ea2b07038e5ac43c`.
- `coordination/inbox/B/exp_001_freeze_readiness.md` is present in `main` and
  records `STATUS=READY_FOR_A_REAL_VALID_GATE`, a full implementation SHA,
  `WORKTREE_CLEAN=true`, matching C data hash and pair evidence, D interface
  verification, passing synthetic smoke, passing tests/contracts/protected
  hashes, no real training, no formal metrics, and `TEST_ACCESS=false`.
- The B implementation commit
  `5ab859b135be02db07d03a24a1827a81ecac656d` and the B readiness head are
  ancestors of the merged main commit.
- This review confirms readiness evidence only. It does not reinterpret B's
  synthetic outputs as formal predictions and does not authorize a real run.

The GitHub CLI was not installed in this environment. Merge identity was
independently verified from the fetched Git commit and its full parent SHAs;
the human-supplied PR number, URL, and merged state were not replaced with a
fabricated API result.

## C and D evidence review

C evidence binds the development dataset to
`69e5a6f656356832f7e1fa6a9774bc404030f32874e18e57e0f38b6a309a1002`,
records `MAX_DATE=20220428`, `TEST_ROWS=0`, `PREFLIGHT=PASS`, preserved valid
row order, and train-only same-user pair feasibility with `PAIR_COUNT=382579`
and `USER_COVERAGE=0.926745516978`.

D evidence records the canonical `FactorizationMachine`, pointwise BCE and
same-user BPR routes, train-only pair sampler, canonical pair coverage fields,
pickle-free NPZ checkpoint with optimizer/resume state, deterministic seeds,
and passing focused interface tests. No real metric claim was accepted from D.

## Expected immutable B package

E will accept a formal B output only after A explicitly opens the real
valid-only gate and every item below is bound to one full clean runtime
`commit_sha`:

- `valid_predictions.csv`
- `run_manifest.json`
- `checkpoint.npz`
- `resolved_config.json`
- `training_history.json`
- `runner_metrics.json`
- a complete artifact SHA-256 inventory
- matching `config_hash`, `data_hash`, `prediction_hash`, and
  `checkpoint_hash`
- matching protected hashes
- `experiment_id=exp_001`
- `executor_role=B`
- `seed=0`
- `dev_max_date<=20220428`
- `worktree_clean=true`
- `test_access=false`
- complete command and start/finish runtime evidence

The current runner writes all six named files, but its completed manifest
artifact list contains only `valid_predictions.csv`, `checkpoint.npz`,
`training_history.json`, and `runner_metrics.json`. It does not include a raw
SHA-256 entry for `resolved_config.json`. The top-level `config_hash` binds the
resolved configuration object, but the formal package requirement also calls
for a complete artifact SHA-256 inventory.

Additionally, the current runtime validator checks the shape of whatever
entries appear in `artifacts` but does not require the complete expected path
set. The independent audit validates top-level provenance and hashes but does
not open each declared artifact and compare its file bytes to the declared
SHA-256. E therefore cannot yet establish `EXPECTED_ARTIFACT_CONTRACT=PASS`.
B must close this in B-owned runner/validator/tests before A authorizes the
real run.

## Prediction contract pre-review

The formal valid prediction contract is ready and the focused checks pass:

- header exactly `row_id,user_id,video_id,score`;
- `row_id` starts at zero and is continuous;
- row count exactly matches official valid;
- `user_id` and `video_id` preserve official valid order;
- repeated user/video rows remain present;
- every score is finite;
- E rejects rather than repairs, deduplicates, or reorders invalid input.

## Verification performed

```text
python -m unittest tests.test_audit tests.test_predictions tests.test_safe_evaluate -v
PASS: 25/25

python scripts/check_protected_files.py
PASS: all seven protected starter files

python scripts/check_prediction_contract.py
PASS: 9/9

python scripts/check_repository_contracts.py
PASS: 21 JSON files plus JSONL/TOML validated

git diff --check
PASS

git diff -- starter/
PASS: no diff
```

No real valid metric was computed or reported. Test access remained false.
