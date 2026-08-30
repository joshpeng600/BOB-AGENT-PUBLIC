# exp_001 PR #25 gate-incident quarantine

STATUS=QUARANTINED_PENDING_HUMAN_INCIDENT_DECISION
ROLE=A
EXPERIMENT_ID=exp_001
APPROVED_AGAINST_COMMIT_SHA=1374a6e4cdbb820b975430c93d514657bc809d63
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
NEXT_RECEIVER=HUMAN

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
quarantined files. A fresh formal valid-only run is forbidden unless a human
selects the fresh-rerun disposition and A later records a new, exact
`REAL_VALID_RUN_ALLOWED` state on `main` bound to a new clean full commit SHA.

