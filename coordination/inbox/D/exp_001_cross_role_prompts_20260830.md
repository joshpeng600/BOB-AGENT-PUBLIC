# exp_001 remaining-work prompts for A, B, C, and E

These prompts are handoff material from D. Each receiving agent must obey
`AGENTS.md` and its own `.codex/agents/<ROLE>.toml`, stay on its role branch,
use synthetic data unless the merged A gate explicitly permits otherwise, and
must not merge its own PR.

## Prompt for A

```text
You are Track 2 role A, the governance, approval, and integration owner.

Repository: https://github.com/joshpeng600/BOB-AGENT
Current verified main before the outstanding fixes:
b7001f693bb412a68398fb2ac47c6c40efe76ca0
Experiment: exp_001

First read AGENTS.md, .codex/agents/A.toml, experiments/exp_001.json,
coordination/current_state.json, governance/manual_interventions.jsonl,
coordination/inbox/D/exp_001_cycle_status_20260830.md, PR #22, and the final E
review evidence for both the audit binding and safe-evaluate race.

Do not implement B or E code and do not authorize a real run yet. Wait until:
1) B updates the existing PR #22 so audit independently binds manifest
experiment_id, normalized repository spec/config paths, approved route,
run_variant, raw config bytes, resolved config, and hashes; all checks pass and E
returns PASS on the final head; and
2) E's separate safe-evaluate fix is reviewed, all checks pass, and its PR is
human-merged.

Then synchronize A-part with the latest main and replace stale governance state
that still refers to PR #18. Record the human decisions for the PR #10
cross-role exception and PR #15 temporary manual gate, plus exact PR/head/merge
SHAs for the final B and E fixes. Freeze one clean full runtime commit SHA and
bind it to experiments/exp_001.json, the approved baseline config, candidate
config, data manifest SHA256
69e5a6f656356832f7e1fa6a9774bc404030f32874e18e57e0f38b6a309a1002,
seed=0, batch_size=8192, epochs=40, patience=4, max_batches=null,
max_runtime_seconds=3600, and valid-only/test=false.

Only after every prerequisite is on main may you record
REAL_VALID_RUN_ALLOWED=true and hand the frozen run to B. Modify only A-owned
governance/coordination files. Run repository contracts, protected checks,
prediction contract, and the full unittest suite. Commit and push A-part, create
an A-part -> main PR, do not merge it yourself, and return the PR link and exact
frozen SHA. No real training, metric computation, or test access.
```

## Prompt for B

```text
You are Track 2 role B, the runner, validator, artifact, and approved-run owner.

Repository: https://github.com/joshpeng600/BOB-AGENT
Continue the existing B-Part and PR #22; do not open a duplicate PR and do not
merge. Current reviewed head is
7477009032f37e57a38099955b7e6aff3c261c19 and implementation commit is
366951c06be3aedddca4f6da7f35e479ed374df4.

First read AGENTS.md, .codex/agents/B.toml,
coordination/inbox/D/exp_001_cycle_status_20260830.md, tools/audit_run.py,
tools/run_experiment.py, tools/validate_contract.py, the run-manifest contract,
and all runner/audit tests.

Fix the independently reproduced audit repository-input blocker. A legal
five-artifact package currently remains accepted after changing only
manifest.experiment_id to exp_forged and manifest.config_path to
../../outside.json while leaving the real exp_001 spec path/hash intact.

Require and verify all of the following in the independent audit:
- experiment_spec_path is a normalized ordinary file under experiments/;
- the exact spec bytes match experiment_spec_hash, parse successfully under the
  experiment-spec contract, have status APPROVED_FOR_IMPLEMENTATION, and have
  the same experiment_id as the run manifest;
- config_path is a normalized ordinary file under configs/ and is exactly the
  candidate or approved baseline route declared by that spec;
- run_variant agrees with the selected route;
- the raw repository config bytes are hash-bound (add a clearly named raw
  config input hash if needed; do not overload the resolved config hash);
- rebuilding resolved_run from the approved raw config and manifest runtime
  inputs exactly matches manifest.config/config_hash and resolved_config.json.

Add synthetic regressions for forged experiment_id, traversal/absolute/symlink
paths, wrong candidate/baseline route, wrong run_variant, raw config drift, and
one positive runner-to-audit package. Preserve all earlier race regressions.
Do not modify tools/safe_evaluate.py, starter/, D model/training code,
governance approval state, approved configs, or experiment scope. Do not train
or access test.

Run focused tests, the full unittest suite, repository contracts, prediction
contract, protected-file checks, and git diff checks on a clean commit. Update
B evidence, push B-Part so PR #22 receives the new head, do not merge, and give
E the exact head plus reproduction commands.
```

## Prompt for C

```text
You are Track 2 role C, the data and feature-contract owner.

Repository: https://github.com/joshpeng600/BOB-AGENT
Experiment: exp_001

C's current data readiness is already complete; do not create a new feature or
change the loss/model. Read AGENTS.md, .codex/agents/C.toml,
coordination/inbox/C/exp_001_real_data_readiness.md,
coordination/inbox/D/exp_001_cycle_status_20260830.md, and the final B audit
contract when available.

At the final pre-run handoff, perform a read-only re-attestation only. Confirm
that data/dev/dataset_manifest.json SHA256 is exactly
69e5a6f656356832f7e1fa6a9774bc404030f32874e18e57e0f38b6a309a1002;
all six declared source SHA-256 values still match their bytes; maximum date is
20220428; test rows are zero; official train/valid row order is unchanged; and
the train-only same-user seed-0 feasibility still reports pair_count=382579,
eligible_users=24290, total_users=26210, user_coverage=0.926745516978.

If every value matches, write a concise C handoff that says
STATUS=DATA_REATTESTED_NO_CHANGE and returns control to A/B. If anything differs,
set STATUS=DATA_MISMATCH_BLOCKED and report the exact file/hash/count; do not
repair or regenerate without human authorization. Do not train, evaluate,
access test, modify starter/, or change features. Commit/push only if a new C
evidence file is actually required; otherwise report NO_COMMIT_REQUIRED.
```

## Prompt for E

```text
You are Track 2 role E, the independent evaluation and immutable-output owner.

Repository: https://github.com/joshpeng600/BOB-AGENT
Base the E implementation branch on the latest merged main, not on unmerged PR
#22, so the E PR contains no B commits.

First read AGENTS.md, .codex/agents/E.toml,
coordination/inbox/D/exp_001_cycle_status_20260830.md,
tools/safe_evaluate.py, tools/prediction_contract.py, tools/audit_run.py, and the
safe-evaluate/audit tests. Do not modify starter/evaluate.py or any protected
starter file.

Fix the reproduced temporary prediction replacement race: safe_evaluate hashes
the original path, can consume temporarily substituted bytes, then sees the
original hash again after restoration and returns success. Evaluation must
instead consume exactly the immutable bytes whose SHA-256 it records. Capture
the prediction through a no-follow fixed handle into a private immutable
snapshot (or parse the captured bytes directly), verify ordinary-file/path
identity and read stability, and ensure every validation/evaluator input comes
from that captured snapshot rather than reopening the mutable source path.
Permanent source drift must fail closed.

Add synthetic tests for temporary swap-and-restore, permanent replacement,
symlink/non-ordinary inputs, normal valid evaluation, and prediction-hash
stability. Do not train, alter predictions, access test, or change official
metric definitions. Run the focused safe-evaluate/prediction/audit tests, full
unittest suite, repository contracts, prediction contract, and protected-file
checks. Commit and push an E role branch, open E -> main PR, do not merge, and
return its link and head SHA.

After B updates PR #22, separately re-review its exact final head. Verify the
audit rejects forged experiment identity/path/route/config evidence while a
positive synthetic runner-to-audit package passes. Return PASS or
CHANGES_REQUIRED. Only after A later opens the merged real-valid gate may E
evaluate B's immutable baseline and candidate valid predictions; cross-check
the evaluator output prediction_hash against each audited run manifest and
never access test.
```
