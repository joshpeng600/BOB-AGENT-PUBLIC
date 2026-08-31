# BOB-AGENT

Track 2 recommendation-agent project. Team member E owns protected evaluation,
quality checks, reproducibility evidence, and final delivery safety.

Start with [docs/EVALUATION_CONTRACT.md](docs/EVALUATION_CONTRACT.md). The
official evaluation files under `starter/` are protected by
`protected_manifest.json` and must not be edited.

Run the E test suite:

```bash
python3 -m unittest discover -s tests -v
```

Coordinate asynchronous A-E experiment work with the safe, read-only default:

```bash
python tools/run_agent_cycle.py --experiment exp_003
```

After A records an explicit bounded valid-only campaign, run up to three newly
completed experiments with separate role worktrees, PRs, and CI gates:

```bash
python tools/run_agent_cycle.py --experiment exp_003 --action run --max-iterations 3
```

The continuous runner stops rather than bypassing missing evidence, manual
artifact transfer, stale routing state, failed PR checks, or policy limits.
Public validation can be automated only inside A's recorded bounds. Hidden-test
access and final approval remain outside every ordinary campaign.

See [docs/AGENT_CYCLE_AUTOMATION.md](docs/AGENT_CYCLE_AUTOMATION.md) for role
dispatch, continuous campaign authorization, stop/resume behavior, Codex quota
recovery, PR/CI monitoring, artifact handoff, and validation gates.
