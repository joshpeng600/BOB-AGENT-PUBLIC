# exp_001 final setup post-merge independent E rereview

STATUS=PASS
ROLE=E
BRANCH=E-Part-final-rereview
REVIEWED_MAIN_SHA=3f972df85ce61f1546b0d55d5096463cdfa418df
PR_33_MERGE_SHA=3f972df85ce61f1546b0d55d5096463cdfa418df
PR_33_HEAD_SHA=387fd28854b6431d96216171b7eb0b25e8520e7e
EXPERIMENT_ID=exp_001

## Independent setup findings

- Approved-run semantics are bound to the A-authored approved experiment,
  approval ancestry, baseline/candidate route, raw config bytes, objective,
  seed, valid-only mode, resolved config, and run commit.
- Formal `max_batches` is required to exactly equal the approved config value,
  including strict `null` equality. A CLI truncation is rejected before data
  access.
- Synthetic smoke uses `status=synthetic_smoke` and
  `evidence_tier=synthetic_only`; it requires an explicit positive batch bound
  and cannot be accepted by the formal auditor.
- `tools/audit_run.py` accepts only `status=completed` formal evidence and
  rejects synthetic, failed, stopped, forged-route, forged-runtime, and
  unrelated-approval records.
- `tools/safe_evaluate.py` rejects an existing output and symlinked output
  directory components, writes an exclusive `O_EXCL` temporary file, fsyncs
  the file, publishes with a no-overwrite hard link, verifies the published
  inode and payload hash, and then rechecks the immutable prediction binding
  and Git state.
- Failure cleanup compares the published inode identity before unlinking. An
  independent adversarial check replaced the published path with an
  attacker-owned inode and confirmed that cleanup preserved the foreign file.
- The protected `starter/` kit is unchanged.

APPROVED_ROUTE_SEMANTICS=PASS
FORMAL_MAX_BATCHES_EXACT_BINDING=PASS
SYNTHETIC_FORMAL_EVIDENCE_ISOLATION=PASS
AUDIT_FORMAL_COMPLETED_ONLY=PASS
SAFE_EVALUATE_EXCLUSIVE_PUBLICATION=PASS
SAFE_EVALUATE_POST_PUBLICATION_HASH_CHECK=PASS
SAFE_EVALUATE_POST_PUBLICATION_PREDICTION_CHECK=PASS
SAFE_EVALUATE_POST_PUBLICATION_GIT_CHECK=PASS
FOREIGN_INODE_CLEANUP=PASS
STARTER_CHANGED=false

## Verification

- Local Windows `python -m unittest discover -s tests -v`:
  `121 passed, 4 skipped`; skips were only unavailable symlink privileges.
- Local Windows `python -m pytest -q -p no:cacheprovider`:
  `117 passed, 4 skipped, 39 subtests passed`.
- PR #33 Ubuntu Actions unit-tests job: `121 passed, 47 subtests passed` with
  no skips, covering the symlink cases unavailable locally.
- Repository contracts: `PASS`, 27 JSON files plus JSONL/TOML validated.
- Prediction contract: `PASS`, 9 of 9.
- Protected-file checks: `PASS`, all seven protected files.
- `git diff --check`: `PASS`.
- `git diff 7dfeb682879aac5ecbcf8f3f84a065e5f54d17b2..3f972df85ce61f1546b0d55d5096463cdfa418df -- starter`:
  no changes.
- PR #33 required GitHub checks: protected files, unit tests, prediction
  contract, and repository contracts all `SUCCESS`.

The synthetic tests exercised both candidate and baseline repository routes,
bounded BPR smoke output, rejection of formal CLI truncation before data
access, rejection of non-completed audit evidence, exclusive publication
races, post-publication tampering, prediction replacement, and Git drift.

## Gate recommendation

RECOMMEND_A_CLOSE_SETUP_CODE_GATE=true
RECOMMEND_A_RECORD_REAL_VALID_RUN_ALLOWED=true

The setup code and post-merge independent E review requirements are satisfied
at the reviewed main SHA. A may now close the setup code gate and record the
separately authorized single fresh valid-only baseline/candidate run. This E
record does not itself activate the run gate, authorize test access, or accept
any prior quarantined evidence.

REAL_DATA_USED=false
TRAINING_PERFORMED=false
FORMAL_EVALUATION_PERFORMED=false
FORMAL_METRICS_PRODUCED=false
PR25_EVIDENCE_READ=false
TEST_ACCESS=false

