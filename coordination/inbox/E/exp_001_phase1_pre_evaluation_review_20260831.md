# exp_001 phase-one pre-evaluation review — E

STATUS=PRE_EVALUATION_READY
ROLE=E
PHASE=PRE_EVALUATION_REVIEW
BASE_MAIN_SHA=d685322f14f6e9137e2fecb85ad2a018f3567318
EVALUATION_COMMIT_SHA=1137e33abbc0c8cea6a6fa684781ad09065db88e
BASELINE_RUN_COMMIT_SHA=NOT_AVAILABLE
CANDIDATE_RUN_COMMIT_SHA=NOT_AVAILABLE
DATA_HASH=69e5a6f656356832f7e1fa6a9774bc404030f32874e18e57e0f38b6a309a1002
DATA_HASH_REAUDITED=false
BASELINE_PREDICTION_HASH=NOT_AVAILABLE
CANDIDATE_PREDICTION_HASH=NOT_AVAILABLE
ARTIFACT_AUDIT=NOT_RUN_WAITING_FOR_TWO_FORMAL_B_PACKAGES
IMMUTABLE_SNAPSHOT=PASS_SYNTHETIC_ONLY
BASELINE_GAUC=NOT_COMPUTED
BASELINE_NDCG_AT_5=NOT_COMPUTED
BASELINE_PRIMARY=NOT_COMPUTED
CANDIDATE_GAUC=NOT_COMPUTED
CANDIDATE_NDCG_AT_5=NOT_COMPUTED
CANDIDATE_PRIMARY=NOT_COMPUTED
IMPROVEMENT_RULE_CHECK=NOT_RUN
PR25_EVIDENCE_USED=false
PREDICTIONS_MODIFIED=false
TRAINING_PERFORMED=false
FORMAL_EVALUATION_PERFORMED=false
FORMAL_METRICS_PRODUCED=false
MAIN_INTEGRATION_PENDING=true
REAL_VALID_RUN_ALLOWED=false
B_FORMAL_PACKAGES_AVAILABLE=false
test_access=false
NEXT_RECEIVER=A

## Scope and conclusion

This is a phase-one E pre-review only. It used repository contracts and
synthetic fixtures. It did not read `data/dev`, train either model, consume a
formal B prediction, evaluate a formal validation artifact, create a metrics
record, or access test.

The manifest contract, prediction contract, artifact-byte binding,
baseline/candidate route binding, exact formal `max_batches` binding,
synthetic/formal evidence isolation, immutable prediction snapshot, exclusive
evidence publication, valid-only enforcement, and test approval path all pass
on the E review commit above.

During this review, the existing output-directory binding incorrectly rejected
normal macOS temporary paths because `/var` is an operating-system-owned alias
to `/private/var`. E fixed only `tools/safe_evaluate.py`: a root-owned symlink
directly below the filesystem root may be bound to its stable ordinary-directory
target, while nested or user-controlled directory symlinks remain rejected.
The output parent must already exist; evaluation does not create an unchecked
directory chain.

The fix is ready for PR, CI, and A integration review. Phase two must not begin
until this E commit is merged, A records an exact real-valid gate on a later
clean `main`, and B supplies both formal packages from the same frozen run
commit.

## Phase-one security checks

- Manifest identity: completed formal evidence requires `experiment_id`, a
  full clean `commit_sha`, `executor_role=B`, approved commit ancestry,
  `data_hash`, `config_input_hash`, `config_hash`, `prediction_hash`,
  `checkpoint_hash`, protected hashes, and a complete five-file artifact
  inventory.
- Approved routes: baseline is bound to
  `configs/approved/baseline_fm.json`; candidate is bound to
  `configs/candidates/bpr_fm.json`. Route, objective, raw config bytes,
  resolved config, seed, mode, and run variant must agree.
- Formal budget: a completed formal run must have `max_batches` exactly equal
  to the approved config value, including strict `null` equality. A formal CLI
  truncation is rejected before data access.
- Evidence tiers: synthetic smoke requires `status=synthetic_smoke`,
  `evidence_tier=synthetic_only`, and a positive batch bound. The independent
  auditor accepts only `status=completed` formal evidence.
- Prediction contract: the header is exactly
  `row_id,user_id,video_id,score`; row IDs are contiguous from zero; row count
  and user/video identities align exactly; duplicate user/video rows are
  preserved; non-finite scores are rejected.
- Immutable evaluation: `safe_evaluate` validates and evaluates a private
  snapshot made from one no-follow source handle, then rechecks source identity,
  bytes, Git commit, worktree state, published evidence identity, and evidence
  hash.
- Safe publication: existing outputs, output replacement races, symlinked
  user directories, post-publication tampering, prediction replacement, and Git
  drift fail closed. Cleanup never removes an attacker-owned replacement inode.
- Split isolation: ordinary prediction validation is valid-only. Test remains
  unavailable without a separate human final approval bound to the exact clean
  commit and protected hashes.

## Frozen repository inputs reviewed

- experiment spec SHA-256:
  `79e4ca963172b61d63aadf14fed5226090a26dc9c30f7cdadb1524bc3468dfe1`
- baseline config SHA-256:
  `612d6478b0508a734f949129b839732a9088bb0fe75d7f5d5026446740f3cc4f`
- candidate config SHA-256:
  `6356cc46d69f1e7efc7c4f0f1927516c26f5d25f4f248d4b505c5061db4c6ae6`
- development data hash declared by the merged C evidence and B precheck:
  `69e5a6f656356832f7e1fa6a9774bc404030f32874e18e57e0f38b6a309a1002`.
  E did not read or independently re-hash `data/dev` during phase one.
- PR #25 evidence was not used, read, reproduced, or compared.

## Verification results

- `python -m unittest tests.test_safe_evaluate -v`: PASS, 12/12.
- `python -m unittest tests.test_audit -v`: PASS, 32/32.
- `python -m unittest tests.test_predictions -v`: PASS, 7/7.
- `python -m unittest tests.test_project_security -v`: PASS, 5/5.
- `python -m unittest tests.test_run_experiment -v`: PASS, 20/20.
- `python -m unittest discover -s tests -v`: PASS, 121/121.
- `python scripts/check_protected_files.py`: PASS, all seven protected files.
- `python scripts/check_prediction_contract.py`: PASS, 9/9.
- `python scripts/check_repository_contracts.py`: PASS, 27 JSON files plus
  JSONL/TOML.
- `python tools/validate_contract.py --type experiment-spec --path experiments/exp_001.json`:
  PASS.
- `git diff --check`: PASS.

All test data was synthetic. No formal score was calculated or published.

## Phase-two blockers and required B handoff

At the reviewed `main`, B has supplied only a cycle precheck and synthetic
smoke record. Its baseline and candidate formal statuses are both
`NOT_STARTED_GATE_BLOCKED`; no immutable formal packages are available.

Before E can start one atomic phase-two evaluation, B must provide baseline and
candidate packages that bind the same frozen `commit_sha`, `data_hash`, seed,
feature set, and full training budget. Each package must include:

- `run_manifest.json`;
- `valid_predictions.csv`;
- `checkpoint.npz`;
- `resolved_config.json`;
- `training_history.json`;
- `runner_metrics.json`;
- every declared SHA-256 and the full runner evidence.

E will reject rather than repair an incomplete, inconsistent, mutable, or
non-formal package. Phase two will create fresh immutable prediction snapshots
and use only the protected official evaluator on valid.
