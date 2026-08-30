# exp_001 PR #25 gate-incident quarantine

STATUS=PERMANENTLY_QUARANTINED_FRESH_RERUN_APPROVED_PENDING_SECURITY_PRECONDITIONS
ROLE=A
EXPERIMENT_ID=exp_001
APPROVED_AGAINST_COMMIT_SHA=4c07e03663e7d13f11547546da7cc6ac3ea5ff98
PR_NUMBER=25
PR_HEAD_SHA=f4f253fe90fc6813aa0d780864b3d49ab46df033
PR_MERGE_SHA=afe5b795abacb408c668f05db1a61b6a5af03879
GATE_STATUS_AT_PRODUCTION=BLOCKED
E_SETUP_REREVIEW=PASS
PR_25_EVIDENCE_ACCEPTED=false
USE_FOR_EXPERIMENT_SELECTION=false
USE_FOR_THRESHOLD_OR_HYPERPARAMETER_DECISIONS=false
COUNT_AS_COMPLETED_ITERATION=false
REPRODUCTION_AUTHORIZED=false
REAL_VALID_RUN_ALLOWED=false
TEST_ACCESS_REPORTED=false
FRESH_VALID_ATTEMPTS_AUTHORIZED_AFTER_GATE_OPEN=1
FRESH_VALID_AUTHORIZATION_ACTIVE=false
NEXT_RECEIVER=B

PR #25 and all files below remain in Git history as incident evidence. They
must not be deleted, rewritten, treated as an accepted experiment result, used
to select a model or configuration, or cited as satisfying `exp_001`:

- `coordination/inbox/E/exp_001_evaluation_result.md`
- `reports/evaluation/exp_001_baseline_metrics.json`
- `reports/evaluation/exp_001_candidate_metrics.json`

The four PR checks passed, but those checks authorize repository integration,
not a formal validation run. At production time the A-owned
`REAL_VALID_RUN_ALLOWED` gate was still blocked. E's independent setup review
in PR #26 therefore explicitly rejected PR #25 as authoritative cycle
evidence and did not reproduce or rely on it.

No score comparison or experiment-selection conclusion may be drawn from the
quarantined files. The repository owner selected the fresh-rerun disposition,
but its single-use authorization is not active yet: the audit route must bind
the approved experiment/spec/config, evaluation must consume the exact bytes
whose hash is recorded, B-owned regressions must pass, and E must independently
rereview the final implementation. Only then may A record a later exact
`REAL_VALID_RUN_ALLOWED=ALLOWED` state on `main` for a new clean full commit
SHA. The future baseline and candidate must share that commit, data hash,
feature set, seed 0, and training budget, and must not reuse PR #25 evidence.
