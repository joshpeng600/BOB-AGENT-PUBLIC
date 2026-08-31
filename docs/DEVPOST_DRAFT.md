# Devpost submission draft

This is copy-ready English copy, not proof that the repository is public, the video is
uploaded, or the Devpost entry is submitted. Replace every bracketed placeholder and
verify claims against the final merged commit.

## Project title

BOB-Agent

## Tagline

A safety-gated five-agent system that proposes, runs, evaluates, and remembers
recommender-system experiments without exposing the hidden test set.

## Inspiration / the problem

Recommendation research is not limited by the number of ideas. It is limited by how
quickly a team can test an idea without losing reproducibility, leaking future data,
or accepting a regression. In a conventional loop, one person may change the model,
move the data boundary, run the evaluation, and interpret the result. That makes fast
iteration possible, but it also makes subtle mistakes hard to see.

We wanted to know whether agentic development could improve both speed and scientific
discipline. BOB-Agent treats each experiment as a governed state transition rather
than an unstructured chat or notebook run.

## What it does

BOB-Agent coordinates five specialized AI-agent roles across one repository. The
system freezes a single-variable hypothesis, enforces role-scoped implementation,
checks the change on synthetic fixtures, runs an explicitly approved public-validation
comparison, independently evaluates immutable predictions, and applies a predeclared
ACCEPT/REJECT rule. Every decision is appended to experiment memory, and a failed
candidate cannot displace the verified champion.

The coordinator reads repository state, identifies the only legal next role, invokes
roles in isolated worktrees, monitors pull requests and CI, resumes interrupted
sessions, and creates SHA-256 manifests for private large-artifact handoff. Its
bounded continuous mode can advance up to A's recorded experiment and role-step
limits; status and report modes provide a dataset-free demonstration.

## How it works

1. A, the controller, freezes the hypothesis, baseline, one scientific variable,
   budget, seed, and success rule.
2. C owns data boundaries and leakage checks; D owns model and training changes.
3. B validates contracts and execution routes, then runs a bounded synthetic smoke.
4. After the public-validation gate is explicitly opened, B produces immutable
   baseline and candidate artifacts from the same clean commit and data hash.
5. E independently audits and evaluates the frozen validation predictions.
6. A applies the strict rule, records ACCEPT or REJECT, and promotes or retains the
   champion.
7. GitHub pull requests, four CI checks, JSON/JSONL contracts, full commit SHAs, and
   SHA-256 manifests make the trajectory reviewable.

`--action run --max-iterations 3` is implemented, but it is deliberately bounded. It
starts only from clean `main` with A's explicit valid-only campaign authorization,
keeps every role/commit/PR/CI decision separate, and grants public-validation work
only when the experiment gate also allows it. Composite work is queued, non-A
evidence is automatically integrated by A, and same-host artifacts reach E through
re-verified private manifests. Waiting or failed roles, unsafe PRs, changed artifacts,
changed authorization, and stop limits still produce a resumable fail-closed stop.

## Five-agent architecture

- **A — Controller:** planning, governance, approvals, integration, and champion
  selection; does not implement or evaluate its own research change.
- **B — Harness & reliability:** runner, validation, manifests, reproducible
  execution, and retry/rollback; does not approve scientific scope.
- **C — Data & features:** data contracts, temporal leakage checks, and feature
  proposals; does not alter model or evaluation logic.
- **D — Models & training:** objectives, samplers, model code, and training loops;
  does not change data boundaries or official metrics.
- **E — Independent evaluator:** immutable prediction audit and metric verification;
  does not train models or modify candidate outputs.

## How we built it / technology stack

We used Python and NumPy for data processing, factorization machines, BPR training,
and metric interfaces. Codex CLI powers isolated, resumable role execution. Git and
GitHub pull requests provide provenance and human-visible handoffs. GitHub Actions run
protected-file, unit-test, prediction-contract, and repository-contract checks. JSON
and JSONL define fail-closed experiment contracts and append-only memory, while
SHA-256 binds protected code and privately transferred artifacts to exact bytes.

## Experiment trajectory

Our reference factorization-machine validation primary was `0.601468756352959`.

- **exp_001 — accepted:** switching from pointwise binary cross-entropy to same-user
  BPR reached `0.603871007132627`, a strict improvement of
  `+0.0024022507796679`.
- **exp_002 — rejected:** increasing BPR negatives per positive from one to two reached
  `0.6032604702292279`, `-0.0006105369033990726` below the exp_001 champion.

The second result matters as much as the first: BOB-Agent rejected a plausible but
worse change and retained exp_001. Both conclusions come from independently committed
public-validation evidence. Quarantined evidence was excluded, and test access was
false.

## Technical challenges

The hardest part was not the model; it was making agent autonomy auditable. We had to
bind configs to experiment identities, distinguish producing commits from approval
commits, prevent baseline/candidate route swaps, verify file bytes before evaluation,
handle large artifacts without Git, and ensure that a synthetic smoke could never be
mistaken for formal evidence. We also designed the coordinator for asynchronous team
members and resumable Codex sessions while preserving role independence.

## Accomplishments

- Reproduced the reference baseline within roughly `0.00013` primary.
- Found and accepted a valid BPR improvement.
- Rejected a follow-up regression and retained the champion in recorded experiment
  state.
- Built a five-role coordinator with bounded continuous campaigns, PR/CI enforcement,
  resumable fail-closed stops, and hashed artifact handoff.
- Protected canonical starter files and enforced clean-commit, data-date, prediction,
  and provenance contracts.
- Created a dataset-free quick start that demonstrates the control plane without
  fabricating a new experiment.

## What we learned

Agents become more useful when they can say “no” with evidence. Explicit role
boundaries and immutable handoffs made failures informative instead of ambiguous.
We also learned that autonomy is not a binary property: bounded continuous execution
is useful precisely because it stops truthfully when human or external evidence is
required.

## Safety and hidden-test isolation

Synthetic fixtures prove interfaces only. Research selection uses the fixed public
validation period ending `20220428`. The ordinary orchestrated workflow never accesses
or scores test data and records `test_access=false`. A final candidate is frozen by
commit, config, and artifact hashes and is intended for an external hidden-test
evaluator; agents should not see hidden labels or local hidden-test metrics.

The repository includes protected starter interfaces, so we do not claim physical
impossibility for a repository owner. We claim—and enforce for the agent workflow—a
clear separation between public-valid research and external hidden-test evaluation.

## Known limitations

- Continuous campaigns require an A-recorded authorization and clean `main`, and stop
  for unresolved role/PR/CI failures, cross-host transfer, or policy limits.
- Automatic public validation is limited to the authorized experiment range and still
  requires each current experiment's recorded gate.
- Same-host artifacts use automatic read-only hash manifests; cross-host artifacts
  still require a private transfer service or human handoff.
- Formal reproduction requires the external KuaiRand dataset.
- Repository publication, licensing, video upload, and Devpost submission remain
  human-controlled release actions.

## What's next

We plan to add managed notification and cross-host artifact-transfer services,
broaden bounded public-validation policy where safe, and connect the existing
label-free final-submission freeze to organizer upload.

## Links

- Public repository: `[REPOSITORY_URL]`
- Public YouTube demo (under three minutes): `[YOUTUBE_URL]`
