# C setup result — exp_001

STATUS=SETUP_READY_WITH_REAL_DATA_PENDING
BASE_MAIN_SHA=6fa3d227e4875161a70879db386dd2fef734b405
ROLE=C
DATA_AVAILABLE=false
DATA_NOT_AVAILABLE_SETUP_ONLY=true
FULL_DEV_BUILDER=tools/build_dev_dataset.py CLI build()
SAMPLED_COMPATIBILITY_API_NOT_RUNNER_READY=true
REAL_DATA_HASH_VERIFIED=false
REAL_MAX_DATE_VERIFIED=false
REAL_PAIR_FEASIBILITY_VERIFIED=false
REAL_TRAINING_PERFORMED=false
FORMAL_METRICS_PRODUCED=false
test_access=false

## Scope and checked files

This is setup evidence only.  No real `data/dev` was available or accessed;
no model training was run; no formal validation metric was produced; and no
test data was accessed.

Reviewed:

- `AGENTS.md`
- `.codex/agents/C.toml`
- `coordination/inbox/C/exp_001_handoff.json`
- `coordination/current_state.json` (read only; owned by A)
- `tools/build_dev_dataset.py`
- `tools/preflight.py`
- `src/data/contracts.py`
- `src/data/feature_registry.py`
- `src/data/manifest.py`
- `tests/test_build_dev_dataset.py`
- `tests/test_build_and_preflight.py`
- `tests/test_leakage_rules.py`
- `tests/test_official_rows.py`

## Builder entry points

- The complete development-data builder is the CLI in
  `tools/build_dev_dataset.py`; it calls `build(source, output, max_date)`.
  It copies the complete train/valid development dataset, filters dates above
  `20220428`, preserves header and source-row order, rejects non-empty output,
  and writes `dataset_manifest.json` with SHA-256 and date/row evidence.
- `build_dev_dataset(data_dir, output_dir, rows_per_log)` is a compatibility
  API for bounded ordered log samples.  It is not a runner-ready replacement
  for the complete CLI builder and must not be used as evidence that complete
  development data is available.

## Contract checks

- Fixed date contract: train `20220408–20220421`; valid `20220422–20220428`;
  test `20220429–20220508`.  Normal development is limited to dates through
  `20220428` and does not expose test through `load_dev_splits`.
- Label contract: `long_view`.
- Row-order contract: raw rows are read in official log-file order and source
  CSV order.  Neither data loader nor builder sorts or deduplicates rows; the
  builder only filters rows after the permitted date.
- Leakage contract: every baseline feature in `FEATURE_REGISTRY` declares
  `fit_split="train"`; registry validation rejects non-train fitting and
  post-impression availability.
- Missing `author_id` is represented as `UNK` by the raw-data contract.

## Test evidence

The requested commands were attempted first with `python`; this environment
has no `python` executable alias.  The same commands were then executed with
the repository virtual-environment Python at
`/Users/baijiaxiandediannao/Documents/GitHub/BOB-AGENT/.venv/bin/python`.

| Command | Result |
| --- | --- |
| `python -m unittest tests.test_build_dev_dataset -v` | PASS (2 tests) |
| `python -m unittest tests.test_build_and_preflight -v` | PASS (4 tests) |
| `python -m unittest tests.test_leakage_rules -v` | PASS (3 tests) |
| `python -m unittest tests.test_official_rows -v` | PASS (1 test) |
| `python -m unittest discover -s tests -v` | PASS (77 tests) |
| `python tools/verify_protected_files.py --manifest protected_manifest.json --repo-root .` | `PROTECTED_FILES=PASS` |
| `python tools/validate_contract.py --type experiment-spec --path experiments/exp_001.json` | `CONTRACT=PASS` |

All data-bearing tests use minimal synthetic fixtures; they are not real-data
pair-feasibility evidence.

## Real-data checks still pending for cycle/data handoff

- Real development-data SHA-256.
- Real maximum date.
- `pair_count`.
- `eligible_users`.
- `total_users`.
- `user_coverage`.
- Confirmation that same-user positive/negative pairs can be constructed from
  real train data only.

For the cycle handoff, B or the data owner must provide a non-Git-tracked
complete `data/dev` produced with the full CLI builder and its
`dataset_manifest.json`.  C must then run read-only preflight and pair
feasibility checks before `REAL_VALID_RUN_ALLOWED` can be considered.  The
handoff must preserve original row order, keep the maximum date at or below
`20220428`, exclude test, and report the six pending evidence fields above.

## PR #9 cross-role fact record and review request

PR #9 (`66f9577`, merged from `C-Part-setup-audit`) changed exactly:

- `tools/build_dev_dataset.py`
- `tests/test_build_dev_dataset.py`

Under `AGENTS.md`, the `tools/` and `tests/` areas are owned by B.  This task
made no changes to either file and did not edit
`governance/manual_interventions.jsonl` or `coordination/current_state.json`.

Request to A: review this evidence-only record and confirm that the current
stage remains setup with real data pending.

Request to B: review the existing PR #9 builder/test changes and confirm the
full CLI builder remains the harness-approved complete-dev-data entry point;
the sampled compatibility API is not runner-ready.
