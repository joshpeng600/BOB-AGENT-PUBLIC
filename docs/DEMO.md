# Three-minute demo

This demo requires no KuaiRand download, no real-data training, and no test access.
It combines a live verification of the product surface with the immutable experiment
history already committed to the repository.

## Prepare

Use Python 3.10+ in a fresh clone:

```bash
git clone https://github.com/joshpeng600/BOB-AGENT-PUBLIC.git
cd BOB-AGENT-PUBLIC
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows PowerShell activation:

```powershell
.venv\Scripts\Activate.ps1
```

Do not download data for this demo. Do not pass `--execute`,
`--allow-real-valid`, or `--auto-merge`.

### Beginner setup in VS Code

1. Open the final `BOB-AGENT-PUBLIC` folder in VS Code.
2. Choose **Terminal → New Terminal** and make the terminal text large enough to read
   in a 1080p recording.
3. Confirm the terminal is on clean `main` with `git status --short --branch`.
4. Activate `.venv`, or create it with the commands above if this is a clean clone.
5. Copy the two commands in the next section exactly. Do not add any execution,
   real-validation, merge, or test-related flags.

## Live commands

Run the complete repository test suite:

```bash
python -m unittest discover -s tests -v
```

Then render the next-cycle report:

```bash
python tools/run_agent_cycle.py --experiment exp_002 --action report
```

The report command is read-only with respect to tracked repository state and
scientific execution. It reads the terminal `exp_002` state and recorded experiment
memory, then writes ignored summaries under `artifacts/agent_cycle/exp_002/`. It does
not create a new proposal or branch, invoke a role, train a model, produce formal
metrics, open a PR, or access test data.

The product also implements
`python tools/run_agent_cycle.py --experiment exp_010 --action run --max-iterations 3`,
but this recording deliberately does **not** run it: continuous mode requires a clean
`main` checkout and an A-recorded bounded campaign authorization, and may advance real
role PRs and approved public-validation work.

Expected facts—not a byte-for-byte terminal transcript—are:

- target experiment: `exp_002`;
- current repository experiment: `exp_002`;
- next legal receiver: `A`;
- public-valid gate: `CONSUMED_BLOCKED`;
- `exp_001`: `KEEP`, delta `+0.0024022507796679`;
- `exp_002`: `REJECT`, delta `-0.0006105369033990726`;
- `test_access=false`.

In plain language, the screen should communicate: **exp_001 improved and was kept;
exp_002 regressed and was rejected; exp_001 is still the champion; A is the next
legal role; hidden test was never accessed.**

Terminal formatting and the generated UTC timestamp may vary. Do not paste a fabricated
transcript into the video; show the actual command output.

## What is live and what is historical

| Segment | Evidence type | Meaning |
| --- | --- | --- |
| Test command | Live execution | Current code and contracts pass locally |
| `--action report` | Live read-only orchestration | Current state routes the next experiment to A |
| exp_001 metrics | Previously committed E valid-only evidence | BPR improved and was accepted |
| exp_002 metrics | Previously committed E valid-only evidence | Two negatives regressed and were rejected |
| Champion | Current committed state | exp_001 remains approved |

The video must not imply that a fresh model trains within three minutes. Synthetic
smoke results, when discussed, demonstrate interfaces only and are not model-quality
metrics.

## Three-minute storyboard

### 0:00–0:25 — Problem

Show the title and repository. Explain: “Recommendation experiments are fast to start
but hard to trust. Data leakage, moving configs, and self-evaluation can silently
select a worse model.”

### 0:25–0:55 — Five-agent design

Open [ARCHITECTURE.md](ARCHITECTURE.md). Explain A plans and gates, C owns safe data,
D implements models, B executes reproducibly, and E independently evaluates immutable
predictions. Point out the PR and CI boundary.

### 0:55–1:35 — Live demo

Run the unit-test command, then the read-only report command. Highlight that A is the
next legal receiver and the valid gate is consumed/closed. Say explicitly: “This
report does not start a new experiment, use real data, or access test.”

### 1:35–2:10 — Learning from success and failure

Open the README experiment table or show the generated report. Explain:

- exp_001 changed pointwise BCE to same-user BPR, improved primary by `0.002402`, and
  was accepted;
- exp_002 increased negatives per positive from one to two, regressed by `0.000611`,
  and was rejected;
- the system retained exp_001 as champion.

### 2:10–2:40 — Safety and reproducibility

Show the four CI workflows, protected hash manifest, experiment history, and
`test_access=false`. Explain that synthetic smoke proves operability, public validation
selects research changes, and hidden test is reserved for external evaluation.

### 2:40–3:00 — Value and next step

Close with: “BOB-Agent makes autonomous ML experimentation reviewable. It remembers
failed ideas, preserves the best result, and can advance an A-authorized bounded
campaign through clean commits, PRs, and CI. It stops and can resume when human or
external evidence is required, without weakening hidden-test isolation.”

## Recording checklist

- Record at 1080p with readable terminal text.
- Keep the final video under three minutes.
- Do not display local paths containing personal information, credentials, private
  artifact locations, or untracked files.
- Do not show or discuss quarantined PR #25 metrics.
- Do not run `step --execute`, `--action run`, real validation, final approval, or test
  operations.
- Verify the uploaded YouTube video in a signed-out browser before Devpost submission.
