# exp_001 E pre-cycle security repair readiness

STATUS=IMPLEMENTATION_READY_PENDING_B_RUNNER_INTEGRATION
ROLE=E
BRANCH=E-Part
BASE_MAIN_SHA=28d4d7480c0a76d5076dc10e694898188af99473
IMPLEMENTATION_COMMIT_SHA=6ee8e268e4d07af3224f933da4e194644c0b1273
EXPERIMENT_ID=exp_001

IMMUTABLE_PREDICTION_INGRESS=PASS
AUDIT_APPROVED_ROUTE_BINDING=PASS
SPEC_STATUS_AND_ID_BINDING=PASS
RUN_VARIANT_AND_CONFIG_ROUTE_BINDING=PASS
RAW_CONFIG_INPUT_HASH_BINDING=PASS
RESOLVED_CONFIG_BINDING=PASS
TEMPORARY_SWAP_AND_RESTORE=FAIL_CLOSED
PERMANENT_PREDICTION_REPLACEMENT=FAIL_CLOSED
PREDICTION_SYMLINK=FAIL_CLOSED

The evaluator opens the source prediction once with no-follow semantics, copies
the bytes through that fixed ordinary-file handle into a private read-only
snapshot, and performs prediction validation and official evaluation only from
that snapshot. It rechecks the original path/handle binding and bytes before
accepting evidence. The recorded prediction hash therefore describes the exact
captured bytes supplied to validation and evaluation.

The independent auditor now keeps the approved experiment spec and selected
repository config open through fixed no-follow handles until artifact audit
completion. It verifies the approved spec status and experiment identity,
candidate/baseline route, run variant, raw `config_input_hash`, and the exact
resolved manifest config and canonical `config_hash`.

CROSS_ROLE_TEST_EXCEPTION=USER_AUTHORIZED_FOR_THIS_SETUP_REPAIR
CROSS_ROLE_TEST_FILES=tests/test_audit.py,tests/test_safe_evaluate.py
E_OWNED_IMPLEMENTATION_FILES=tools/audit_run.py,tools/safe_evaluate.py

FOCUSED_AUDIT_TESTS=PASS_26_OF_26
FOCUSED_SAFE_SECURITY_TESTS=PASS_3_OF_3
PYTEST=PASS_104_FAIL_1_EXPECTED_B_INTEGRATION_DEPENDENCY
UNIT_TESTS=PASS_104_OF_105_WITH_1_EXPECTED_B_INTEGRATION_DEPENDENCY
EXPECTED_INTEGRATION_FAILURE=tests.test_run_experiment.RunExperimentTests.test_repository_inputs_produce_an_auditable_completed_package
EXPECTED_FAILURE_REASON=current_main_runner_does_not_yet_emit_config_input_hash
REPOSITORY_CONTRACTS=PASS
PROTECTED_HASHES=PASS
PREDICTION_CONTRACT=PASS_9_OF_9
PYTHON_USED_FOR_FULL_SUITE=/opt/anaconda3/bin/python
SYSTEM_PYTHON_NOTE=python3 lacked pytest and numpy; no dependency installation was attempted

REAL_VALID_RUN_ALLOWED=false
REAL_DATA_TRAINING_PERFORMED=false
FORMAL_EVALUATION_PERFORMED=false
FORMAL_METRICS_PRODUCED=false
QUARANTINED_PR25_EVIDENCE_READ=false
TEST_ACCESS=false

BLOCKERS=B-Part commit 6a73236e8d3e11aa9687f7d44ed7cbb97aed6110
contains the complementary runner emission, but it is not yet on this E branch
or main. After B reaches main, this E head must be integrated and the combined
clean tree must pass the full suite before independent rereview and any A gate
change.

NEXT_RECEIVER=A
