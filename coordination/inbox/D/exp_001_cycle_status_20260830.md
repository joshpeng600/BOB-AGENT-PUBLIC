# exp_001 D cycle status and cross-role handoff

STATUS=D_READY_WAITING_ON_EXTERNAL_GATES
ROLE=D
BRANCH=D-Part
BASE_MAIN_SHA=b7001f693bb412a68398fb2ac47c6c40efe76ca0
EXPERIMENT_ID=exp_001
PR22_URL=https://github.com/joshpeng600/BOB-AGENT/pull/22
PR22_REVIEWED_HEAD=7477009032f37e57a38099955b7e6aff3c261c19
PR22_IMPLEMENTATION_COMMIT=366951c06be3aedddca4f6da7f35e479ed374df4
DATA_MANIFEST_SHA256=69e5a6f656356832f7e1fa6a9774bc404030f32874e18e57e0f38b6a309a1002
EXPERIMENT_SPEC_SHA256=79e4ca963172b61d63aadf14fed5226090a26dc9c30f7cdadb1524bc3468dfe1
REAL_VALID_RUN_ALLOWED=false
REAL_TRAINING_PERFORMED=false
FORMAL_VALID_METRICS_PRODUCED=false
TEST_ACCESS=false

## Completed and independently checked

- D setup PR #14 is merged. The canonical `src.models.FactorizationMachine`,
  pointwise BCE, same-user BPR sampler/training path, pair-coverage fields, and
  pickle-free checkpoint contract remain present on `main`.
- A fresh LF checkout of `D-Part` at the base above passed all D-focused tests:
  models `3/3`, training `7/7`, and the standalone protected-file verifier.
- No file under `src/models/` or `src/training/` changed between the merged base
  and reviewed PR #22 head. No new D implementation gap was found.
- C's committed evidence binds the development dataset to the manifest hash
  above, `MAX_DATE=20220428`, `TEST_ROWS=0`, and train-only same-user feasibility:
  `PAIR_COUNT=382579`, `ELIGIBLE_USERS=24290`, `TOTAL_USERS=26210`,
  `USER_COVERAGE=0.926745516978`.
- B PR #22 head `7477009` closes the four originally reported artifact/input
  races: interrupt fail-closed status, raw spec/config drift, declared data-source
  hashes plus a private execution snapshot, and replacement during fixed-handle
  artifact validation. Its GitHub contracts, prediction, tests, and protected-file
  checks passed. The PR remains open and unmerged.
- E independently reproduced those four closures and a positive synthetic
  runner-to-audit package. E then found two new, separately reproducible gates:
  the auditor accepts a forged manifest experiment/config route, and
  `safe_evaluate` can consume temporarily replaced prediction bytes that are
  restored before its final path hash.
- A has a local draft at `93708a07ad1c8029b02b15163d5769f6bbb5e1e6`,
  but it was intentionally not pushed because it predates the two new E
  blockers. It is not merged governance evidence and must be refreshed by A.

## Current blockers outside D ownership

1. B must bind the audited manifest to the repository experiment spec and raw
   candidate/baseline config, including normalized paths, experiment identity,
   run variant, route, and resolved configuration.
2. E must make validation evaluation consume the exact immutable bytes whose
   SHA-256 is recorded, rather than reopening a mutable prediction path.
3. E must re-review the final B head after item 1 is fixed.
4. A must merge reviewed B/E fixes through human-approved PRs, update the stale
   governance state, record the required manual decisions, and only then set
   `REAL_VALID_RUN_ALLOWED=true` on `main` with one frozen full commit SHA.

The copy-ready prompts for these owners are in
`coordination/inbox/D/exp_001_cross_role_prompts_20260830.md`.

## Remaining D work

D has no authorized code change at this checkpoint. D must not run the formal
baseline or candidate; repository rules assign approved-run execution to B.
D remains responsible for a model/training repair only if a later synthetic or
formal run provides a concrete failure trace rooted in `src/models/` or
`src/training/`, or if A issues a new cycle handoff. Any such repair must:

- preserve the approved FM family, features, loss-only hypothesis, seed, and
  hyperparameters;
- be reproduced first with a minimal synthetic fixture;
- stay within D-owned model/training files and D inbox evidence;
- run models/training focused tests and the full repository gates;
- never read test data or tune from validation/test metrics.

Until one of those triggers occurs, `NO_D_CODE_CHANGE_REQUIRED=true`.

## Verification in the clean D checkout

```text
python -m unittest discover -s tests/models -v
PASS: 3/3

python -m unittest discover -s tests/training -v
PASS: 7/7

python tools/verify_protected_files.py --manifest protected_manifest.json --repo-root .
PASS
```

DATA_REQUIRED_FOR_CURRENT_D_WORK=false
REAL_TRAINING_PERFORMED=false
test_access=false
