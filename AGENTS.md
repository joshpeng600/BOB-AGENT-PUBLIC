# Track 2 repository operating rules

This repository is a five-member, five-agent workspace. The bootstrap phase builds a safe and reproducible experiment system; it does not authorize new-model research.

## Fixed task contract

- Task: rank items within each user.
- Label: `long_view`.
- Metrics: GAUC and nDCG@5.
- Primary metric: arithmetic mean of GAUC and nDCG@5.
- Data split: train `20220408–20220421`, validation `20220422–20220428`, test `20220429–20220508`, as implemented by `starter/data.py`.
- Reference baseline: FM validation primary score `0.6016`.
- The canonical task evidence is the protected seven-file `starter/` kit. Agents must not replace the date split with random, user, or row splits.

## Hard safety rules

1. Never modify files under `starter/` during ordinary work. Canonical restoration is allowed only with explicit human authorization, a matching record in `governance/manual_interventions.jsonl`, exact source/hash verification, and A-reviewed protected-hash updates.
2. `starter/evaluate.py`, `starter/data.py`, `starter/submit.py`, and `starter/baseline_scores.json` are protected by SHA-256 pins in both `governance/protected_files.json` and `protected_manifest.json`. Preserve `.gitattributes`; protected text uses canonical LF across platforms.
3. Never read, score, tune on, select from, or report hidden-test labels or hidden-test metrics. Local hidden-test scoring is permanently disabled. The release-only workflow uses `tools/final_approval.py` to verify a clean frozen commit and human approval, then `tools/final_submission.py` freezes one label-free submission for organizer-side scoring.
4. Validation is the only split used for feature, model, threshold, or hyperparameter decisions.
5. Git provenance uses contract-specific fields. Approval records (`experiment_spec`, approved configs, current state, and A handoffs) use `approved_against_commit_sha`; C/D proposals may add `implementation_commit_sha` when they reference implemented code; run/evaluation evidence uses `commit_sha`, which must equal the clean HEAD that produced the evidence. All populated SHA fields are complete lowercase 40-character SHAs. `exp_id`, `base_commit`, `commit`, and `frozen_commit` are forbidden aliases.
6. The canonical experiment identifier field is `experiment_id`; `exp_id` is not accepted.
7. Do not commit data, credentials, predictions, checkpoints, virtual environments, or generated artifacts.
8. Do not weaken prediction/audit checks merely to make tests pass, and never claim PASS when required evidence is absent.
9. Run `python3 -m unittest discover -s tests -v` before requesting review.

## Roles and write authority

- A — planning, approval, and integration. Owns experiment specifications, `AGENTS.md`, `governance/`, `.github/`, `.codex/`, approved-config promotion, and repository integration. A does not implement or evaluate its own research change.
- B — harness implementation, approved-run execution, and reliability. Owns the runner, preflight, validators, `tests/`, retry/rollback behavior, manifests, and reproducible execution. B does not approve its own configuration or independently change the scientific scope.
- C — data and features. Owns data contracts, leakage checks, feature definitions, and feature proposals. C does not change model/training logic, protected files, or approval state.
- D — models and training. Owns model implementations, loss functions, samplers, training loops, checkpoints, and model proposals. D does not change official evaluation, data boundaries, protected files, or approval state.
- E — independent evaluation and final release gate. Owns immutable prediction evaluation, metrics verification, audit evidence, and human-approved final release. E does not train models, modify candidate outputs, or approve its own evaluation exception.

Model and training work belongs to D; harness and execution belong to B; feature/data work belongs to C; all remain outside E's evaluation tooling.

Agents write only in their owned area unless A records an exception in `governance/manual_interventions.jsonl`. All proposals enter through `coordination/inbox/<ROLE>/` and retain author, `experiment_id`, the SHA field required by `governance/contract_fields.json`, and decision state.

## Experiment stage gates

- `IMPLEMENTATION_ALLOWED`: A's governance baseline is merged to `main`, protected hashes pass, and the role branch is synchronized with `origin/main`. This gate permits code and synthetic-fixture work only; it never permits test access.
- `SYNTHETIC_SMOKE_ALLOWED`: implementation is committed on a clean worktree and repository contracts, protected files, and unit tests pass. Synthetic smoke results prove interface operability only and are not metric evidence.
- `REAL_VALID_RUN_ALLOWED`: the governance PR is human-merged, C confirms the development-data date/hash and same-user pair feasibility, B freezes a clean full-SHA implementation, baseline and candidate use the same B commit/data/features/seed/budget, and required GitHub checks are enforced or a human-approved substitute is recorded. Test access remains forbidden.

## Git rules

- Work on role branches; do not commit directly to `main`.
- `main` accepts changes only through reviewed pull requests with required status checks. Repository administrators must enable GitHub branch protection/rulesets; workflow files alone cannot prevent an already accepted direct push.
- Keep commits scoped and reproducible. Never force-push shared branches or rewrite shared history without a recorded human instruction.
- Pull requests changing protected hashes require human approval and a matching manual-intervention record.
- Candidate configs live in `configs/candidates/`. Only A may promote a reviewed candidate to `configs/approved/`.

## Improvement and escalation

An improvement must exceed the current approved primary score by `epsilon` from `governance/policy.json`. After the configured number of consecutive non-improving completed trials, stop automatic iteration and request a human decision. One automatic repair attempt is allowed for an infrastructure-only failure; scientific or policy failures are never auto-repaired.

Escalate to a human immediately when a protected file is missing or changed, test access is requested or detected, results are irreproducible, the commit SHA is missing or dirty, role permissions conflict, data leakage is suspected, a run exceeds its time limit, baseline/task evidence conflicts with this contract, or a change would require force-push/history rewrite. Record the decision in `governance/manual_interventions.jsonl` before resuming.
