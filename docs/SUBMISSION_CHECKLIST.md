# Submission checklist

This checklist separates repository-verifiable work from human-controlled release
actions. Do not mark an item complete without evidence from the final merged commit.

## Repository package

- [x] README explains the product, five-agent architecture, quick start, verified
  trajectory, safety boundaries, limitations, and roadmap.
- [x] Architecture, demo, and Devpost draft documents exist.
- [ ] Packaging PR merged after all four required Actions checks pass.
- [ ] Clean-clone quick start verified on a machine/environment that does not contain
  the development dataset.
- [ ] Final merged SHA recorded in the Devpost notes.

## Verification

- [ ] `python -m pytest -q` passes on the final merged commit.
- [ ] `python -m unittest discover -s tests -v` passes on the final merged commit.
- [ ] `python scripts/check_repository_contracts.py` passes.
- [ ] `python scripts/check_protected_files.py` passes.
- [ ] `python scripts/check_prediction_contract.py` passes.
- [ ] `python tools/run_agent_cycle.py --experiment exp_003 --action report` shows A
  as next receiver, exp_001 KEEP, exp_002 REJECT, and `test_access=false` without
  creating an experiment or formal metrics.
- [ ] `git diff -- starter/` is empty.
- [ ] Final tracked worktree is clean.

## Public-release safety

- [ ] No tracked datasets, predictions, checkpoints, run artifacts, `.env` files,
  credentials, access tokens, or private keys.
- [ ] Full Git history scanned for secret patterns; findings reviewed without printing
  secret values into logs.
- [ ] Full Git history scanned for unexpectedly large blobs or committed artifacts.
- [ ] `.gitignore` covers data, artifacts, checkpoints, predictions, environments, and
  credential files.
- [ ] PR #51 status manually confirmed. If it remains open and is superseded by the
  merged exp_002 decision and PR #54, close it with a clear superseded note.
- [x] Repository owner explicitly selected the MIT License; the license and authorization
  record are committed.
- [x] Repository owner explicitly authorized public visibility.
- [x] Public repository is accessible without authentication at
  https://github.com/joshpeng600/BOB-AGENT-PUBLIC.

## Video

- [ ] Record the workflow from [DEMO.md](DEMO.md) without real data or test access.
- [ ] Video is under three minutes and terminal text is readable.
- [ ] Video distinguishes live tests/reporting from historical valid-only evidence.
- [ ] No personal paths, credentials, private artifact locations, or quarantined PR #25
  metrics are visible.
- [ ] Upload to YouTube as public and verify playback while signed out.

## Devpost

- [ ] Replace the remaining `[YOUTUBE_URL]` placeholder in the submission copy; the public
  repository URL is already populated.
- [ ] Review the final text for technical execution, innovation/problem insight,
  impact/relevance, feasibility/practicality, and presentation.
- [ ] Describe `--action run --max-iterations 3` as an implemented, A-authorized
  bounded campaign with fail-closed stop/resume; do not claim absolute unattended
  execution, unrestricted automatic public-valid, repository publication, or external
  submission.
- [ ] Submit before `2026-09-01 12:00 SGT`, leaving time for link verification.

## Non-negotiable boundary

- [x] Ordinary agent workflow reports `test_access=false`.
- [ ] Final submission is checked for format and hashes only, then sent to the external
  hidden-test evaluator without local hidden labels or metrics being exposed to agents.
