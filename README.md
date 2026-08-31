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

See [docs/AGENT_CYCLE_AUTOMATION.md](docs/AGENT_CYCLE_AUTOMATION.md) for role
dispatch, Codex quota recovery, PR/CI monitoring, artifact handoff, and the
explicit real-validation gate.
