# Track 2 repository operating rules

This repository is a five-member, five-agent workspace. The bootstrap phase builds a safe and reproducible experiment system; it does not authorize new-model research.

## Fixed task contract

- Task: rank items within each user.
- Label: `long_view`.
- Metrics: GAUC and nDCG@5.
- Primary metric: arithmetic mean of GAUC and nDCG@5.
- Data split: the canonical date split implemented by `starter/data.py`; agents must not replace it with random, user, or row splits.
- Reference baseline: FM validation primary score `0.6016`.
- Evidence status: the task contract above is supplied by the Track 2 brief. It remains operationally unverified until the missing `starter/` tree is restored and B validates it.

## Hard safety rules

1. Never modify files under `starter/`. In particular, `starter/evaluate.py` and `starter/baseline_scores.json` are protected by SHA-256 pins in `governance/protected_files.json`.
2. Never read, score, tune on, select from, or report test labels or test metrics during an ordinary experiment. Test evaluation requires a recorded human decision and a release-only workflow.
3. Validation is the only split used for feature, model, threshold, or hyperparameter decisions.
4. Every artifact and reported metric must bind to the complete 40-character Git commit SHA that produced it. Branch names, tags, and abbreviated SHAs are insufficient.
5. Do not commit data, credentials, predictions, checkpoints, virtual environments, or generated artifacts.
6. Do not claim a check passed when the required file, tool, data, dependency, or output is absent.

## Roles and write authority

- A — controller and integrator. Owns `AGENTS.md`, `governance/`, `.github/`, `.codex/`, approved-config promotion, and repository integration. A may review all areas but may not silently rewrite another role's result.
- B — validation and contracts. Owns `tests/` and validator implementation under `scripts/`; confirms task semantics, date split, baseline reproduction, prediction schema, and CI behavior. B does not propose research changes.
- C — feature proposals. Writes feature proposals and candidate feature configs only; no model-family changes, protected-file edits, or approval/promotion.
- D — model proposals. Writes model proposals and candidate model configs only; no feature-definition changes, protected-file edits, or approval/promotion.
- E — execution and reproducibility. Runs approved experiments and writes manifests, metrics, and run reports; does not change evaluation logic or approve its own run.

Agents write only in their owned area unless A records an exception in `governance/manual_interventions.jsonl`. All proposals enter through `coordination/inbox/<ROLE>/` and must retain author, commit SHA, and decision state.

## Git rules

- Work on role branches; do not commit directly to `main`.
- `main` accepts changes only through reviewed pull requests with required status checks. Repository administrators must enable GitHub branch protection/rulesets; workflow files alone cannot prevent an already accepted direct push.
- Keep commits scoped and reproducible. Never force-push shared branches or rewrite shared history without a recorded human instruction.
- Pull requests changing protected hashes require human approval and a matching manual-intervention record.
- Candidate configs live in `configs/candidates/`. Only A may promote a reviewed candidate to `configs/approved/`.

## Improvement and escalation

An improvement must exceed the current approved primary score by `epsilon` from `governance/policy.json`. After the configured number of consecutive non-improving completed trials, stop automatic iteration and request a human decision. One automatic repair attempt is allowed for an infrastructure-only failure; scientific or policy failures are never auto-repaired.

Escalate to a human immediately when a protected file is missing or changed, test access is requested or detected, results are irreproducible, the commit SHA is missing or dirty, role permissions conflict, data leakage is suspected, a run exceeds its time limit, baseline/task evidence conflicts with this contract, or a change would require force-push/history rewrite. Record the decision in `governance/manual_interventions.jsonl` before resuming.
