# exp_001 B pre-cycle security readiness

STATUS=READY_FOR_E_SECURITY_REREVIEW
ROLE=B
BRANCH=B-Part
MAIN_SHA_REVIEWED=28d4d7480c0a76d5076dc10e694898188af99473
IMPLEMENTATION_COMMIT_SHA=5cc237161909b592df0bdb24a8c6f47543c77e92
FINAL_HEAD_SHA=reported_after_the_readiness_commit_to_avoid_git_self_reference
EXPERIMENT_ID=exp_001
SPEC_IDENTITY_BOUND=true
SPEC_BYTES_BOUND=true
CONFIG_ROUTE_BOUND=true
CONFIG_INPUT_HASH_BOUND=true
RESOLVED_CONFIG_REBUILT=true
FORGED_ROUTE_REJECTED=true
POSITIVE_RUNNER_TO_AUDIT=PASS
E_OWNED_FILES_MODIFIED=false
SYNTHETIC_ONLY=true
REAL_DATA_TRAINING_PERFORMED=false
FORMAL_VALID_METRICS_PRODUCED=false
PR25_EVIDENCE_USED=false
TEST_ACCESS=false
PROTECTED_HASHES=PASS
REPOSITORY_CONTRACTS=PASS
PREDICTION_CONTRACT=PASS
PYTEST=PASS_102_TESTS
UNIT_TESTS=PASS_102_OF_102
TARGETED_SECURITY_TESTS=PASS_48_OF_48
BLOCKERS=none
NEXT_RECEIVER=HUMAN_FOR_MERGE

## Scope and evidence

- `tools/run_experiment.py` now records `run_variant`, the raw repository
  `config_input_hash`, and the runtime `mode`/`max_batches` inputs used to build
  the resolved run configuration.
- `tools/validate_contract.py` binds completed evidence to a normalized,
  non-symlink repository experiment spec and config, verifies the exact raw
  bytes, enforces the approved baseline/candidate route, and reconstructs the
  resolved configuration before artifact acceptance.
- Synthetic regressions reject forged experiment identity, invalid or swapped
  routes, unsafe POSIX/Windows paths, symlinks, unapproved specs, missing or
  incorrect raw config hashes, and resolved-config drift.
- A positive synthetic repository-spec runner package passes the independent
  `audit_manifest()` entry point.

No E-owned implementation, model/training science, protected file, real-data
artifact, formal metric, quarantined PR #25 evidence, or test split was used or
modified.

## Validation

```text
/opt/anaconda3/bin/python -m pytest -q
102 passed in 0.40s

/opt/anaconda3/bin/python -m unittest discover -s tests -v
Ran 102 tests in 0.358s — OK

/opt/anaconda3/bin/python -m unittest tests.test_run_experiment tests.test_audit tests.test_protected_and_contracts -v
Ran 48 tests in 0.110s — OK

/opt/anaconda3/bin/python scripts/check_repository_contracts.py
PASS — 27 JSON files plus JSONL/TOML validated

/opt/anaconda3/bin/python scripts/check_protected_files.py
PASS — canonical seven files unchanged

/opt/anaconda3/bin/python scripts/check_prediction_contract.py
PASS — 9 of 9 tests

git diff --check
PASS

git diff -- starter/
PASS — no output
```
