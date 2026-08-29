# C: add time-safe data contract, audit, and feature governance

## What changed

- Added a named, index-compatible raw-row interface and train/validation-only loader.
- Added read-only CSV auditing with SHA-256 manifest generation.
- Added a deterministic, validation-safe dev-dataset builder plus correctness tests.
- Added a train-only feature registry and leakage-rule tests.

## Verified

See `docs/data_contract.md`. No test metric is used or reported by these tools.

## Validation

```bash
python -m unittest tests.test_build_dev_dataset tests.test_leakage_rules
python tools/audit_data.py --data-dir baseline/KuaiRand-Pure/data
```

## Review request

- B: call the audit before automated experiments and retain its output with the run logs.
- D: consume `load_dev_splits()` and register any added feature before training.
- A: use the documented hypotheses as candidates only; C does not choose the final experiment.
