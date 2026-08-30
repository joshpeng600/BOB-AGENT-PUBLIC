# exp_001 setup completion and cycle-approval hold — A

STATUS=SETUP_COMPLETE_AWAITING_EXPLICIT_USER_CYCLE_APPROVAL
ROLE=A
BASE_MAIN_SHA=92d4804d719826656e9466c7ff44c4d96b0e5711
EXPERIMENT_ID=exp_001
SETUP_COMPLETE=true
CYCLE_STARTED=false
REAL_VALID_RUN_ALLOWED=READY_PENDING_EXPLICIT_USER_CYCLE_APPROVAL
AUTHORIZED_ATTEMPTS_ACTIVE=0
NEXT_RECEIVER=USER_FOR_CYCLE_APPROVAL
PR25_QUARANTINE=PERMANENT_NOT_ACCEPTED
TRAINING_PERFORMED=false
FORMAL_METRICS_PRODUCED=false
TEST_ACCESS=false

## Final setup evidence

- PR #33 head `387fd28854b6431d96216171b7eb0b25e8520e7e` merged as
  `3f972df85ce61f1546b0d55d5096463cdfa418df` with all four required
  GitHub checks successful.
- E independently reviewed that merged main in commit
  `b3095989800f98b368ec9edf2dbc942ef56096a3`.
- E's PASS evidence merged through PR #34 as
  `92d4804d719826656e9466c7ff44c4d96b0e5711`, again with all four
  required checks successful.
- E confirmed approved-route semantics, exact formal `max_batches`, synthetic
  evidence isolation, formal-completed-only audit, exclusive evidence
  publication, post-publication output/prediction/Git checks, foreign-inode
  cleanup, and unchanged protected starter files.
- E explicitly reported no real data use, no training, no formal evaluation or
  metrics, no reading of PR #25 evidence, and no test access.

Evidence: `coordination/inbox/E/exp_001_setup_final_post_merge_rereview.md`.

## Governance decision

Setup is complete. The setup-only cross-role authorization is closed and does
not become standing permission. PR #25 remains permanently quarantined and
must never be used for selection, comparison, or reproduction evidence.

The user instructed A to announce setup completion and wait for a new explicit
approval before beginning cycle. Therefore readiness is fail-closed: no real
valid-only run is authorized, the separately approved fresh attempt is not
active, and B must not execute training. After renewed user approval, A must
record a separate exact `REAL_VALID_RUN_ALLOWED=ALLOWED` decision against the
then-current clean full `main` SHA before any cycle action begins.
