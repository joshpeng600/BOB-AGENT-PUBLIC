# E: protected evaluation, audit, and evidence gate

## What changed

- Added an immutable copy of the official evaluator and its protected hashes.
- Added strict row-aligned prediction validation.
- Added a valid-only safe evaluation command.
- Added independent run-manifest and final-approval checks.
- Added metrics, run-manifest, experiment-summary, and PR evidence templates.

## Safety properties

- Official evaluation logic is not modified.
- Model, training, and feature code are outside this change.
- Test operations fail closed without a frozen full SHA, clean worktree,
  matching protected hashes, and explicit human approval.
- Contract tests cover headers, lengths, row IDs, alignment, duplicate
  user-video pairs, NaN/Inf, dates, hashes, commits, and forbidden commands.

## Verification

```bash
python3 -m unittest discover -s tests -v
python3 -m tools.safe_evaluate --help
python3 -m tools.audit_run --help
python3 -m tools.final_approval --help
```

## Reviewer checklist

- [ ] Confirm protected hashes against the official Starter Kit.
- [ ] Confirm no model, training, feature, or official-evaluator change.
- [ ] Review every rejection test; do not weaken a contract to make it pass.
- [ ] Reproduce a validation evaluation from a clean clone.
- [ ] Obtain human approval only after the final commit is frozen.
