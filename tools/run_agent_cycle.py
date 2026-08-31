#!/usr/bin/env python3
"""Safely coordinate asynchronous A-E experiment-cycle work.

The coordinator is deliberately conservative: status/report operations are
read-only, role execution requires ``--execute``, formal validation additionally
requires an A-recorded gate, and large artifacts are never sent to Git.  The
continuous ``run`` action is bounded by an A-recorded campaign authorization;
it never creates or expands that authorization itself.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


ROLES = ("A", "B", "C", "D", "E")
REQUIRED_CHECKS = {
    "protected-files / verify-protected-files",
    "unit-tests / tests",
    "prediction-contract / prediction-contract",
    "repository-contracts / contracts",
}
PROTECTED_AUTOMERGE_PATHS = {
    ".gitattributes",
    "protected_manifest.json",
    "governance/protected_files.json",
}
RELEASE_ONLY_AUTOMERGE_PATHS = {
    "contracts/final_approval.template.json",
    "tools/final_approval.py",
}
E_OWNED_TOOL_PATHS = {
    "tools/audit_run.py",
    "tools/safe_evaluate.py",
}
TERMINAL_WORDS = ("COMPLETED", "REJECTED", "ACCEPTED", "CLOSED")
EXPERIMENT_RE = re.compile(r"^exp_(\d{3,})$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


class CycleError(RuntimeError):
    """Fail-closed cycle validation error."""


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class CampaignAuthorization:
    """Validated, A-recorded limits for one continuous valid-only campaign."""

    experiment_ids: tuple[str, ...]
    max_completed_experiments: int
    max_role_steps: int
    automatic_public_valid: bool
    authorization_hash: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def run_command(
    argv: Sequence[str],
    *,
    cwd: Path,
    input_text: str | None = None,
    timeout_seconds: int | None = None,
) -> CommandResult:
    try:
        completed = subprocess.run(
            list(argv),
            cwd=str(cwd),
            input=input_text,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout.decode("utf-8", "replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode("utf-8", "replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        return CommandResult(124, stdout, stderr or "command timed out")
    return CommandResult(completed.returncode, completed.stdout, completed.stderr)


def require_success(result: CommandResult, label: str) -> str:
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "no output"
        raise CycleError(f"{label} failed ({result.returncode}): {detail}")
    return result.stdout.strip()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CycleError(f"cannot read JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise CycleError(f"expected JSON object in {path}")
    return value


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def repository_root(start: Path | None = None) -> Path:
    start = (start or Path.cwd()).resolve()
    result = run_command(("git", "rev-parse", "--show-toplevel"), cwd=start)
    return Path(require_success(result, "git repository lookup")).resolve()


def require_clean_worktree(repo: Path) -> str:
    status = require_success(
        run_command(("git", "status", "--porcelain"), cwd=repo),
        "git status",
    )
    if status:
        raise CycleError("worktree is not clean; refusing role execution")
    return require_success(
        run_command(("git", "rev-parse", "HEAD"), cwd=repo), "git HEAD"
    )


def verify_protected(repo: Path) -> None:
    result = run_command(
        (sys.executable, "scripts/check_protected_files.py"), cwd=repo
    )
    require_success(result, "protected-file verification")


def normalize_receivers(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        tokens = [str(item) for item in value]
    else:
        tokens = re.split(r"(?:_AND_|\s*(?:/|,|\+|&)\s*)", str(value).upper())
    receivers: list[str] = []
    for token in tokens:
        token = token.strip().upper()
        if not token:
            continue
        if token not in ROLES:
            raise CycleError(f"unsupported next_receiver value: {token}")
        if token not in receivers:
            receivers.append(token)
    return receivers


def is_terminal_state(state: Mapping[str, Any]) -> bool:
    status = " ".join(
        str(state.get(key, "")).upper()
        for key in ("state", "status", "decision")
    )
    return any(word in status for word in TERMINAL_WORDS)


def next_experiment_id(experiment_id: str) -> str:
    match = EXPERIMENT_RE.fullmatch(experiment_id)
    if not match:
        raise CycleError(f"invalid experiment identifier: {experiment_id}")
    return f"exp_{int(match.group(1)) + 1:03d}"


def select_target_experiment(
    requested: str | None,
    current_experiment: Mapping[str, Any],
    current_state: Mapping[str, Any],
) -> str:
    active = str(
        current_experiment.get("experiment_id")
        or current_state.get("active_experiment_id")
        or ""
    )
    if not active:
        if not requested:
            raise CycleError("no active experiment and no --experiment supplied")
        return requested
    if not requested:
        return next_experiment_id(active) if is_terminal_state(current_experiment) else active
    if requested == active:
        return requested
    if is_terminal_state(current_experiment) and requested == next_experiment_id(active):
        return requested
    raise CycleError(
        f"requested {requested} is inconsistent with active {active} and its state"
    )


def determine_receivers(
    target: str,
    current_experiment: Mapping[str, Any],
    current_state: Mapping[str, Any],
) -> list[str]:
    active = str(current_experiment.get("experiment_id", ""))
    if target != active and is_terminal_state(current_experiment):
        return ["A"]
    return normalize_receivers(
        current_state.get("next_receiver") or current_experiment.get("next_receiver")
    )


def real_valid_gate_status(current_state: Mapping[str, Any]) -> str:
    stage_gates = current_state.get("stage_gates", {})
    if not isinstance(stage_gates, Mapping):
        return "MISSING"
    gate = stage_gates.get("REAL_VALID_RUN_ALLOWED", {})
    if not isinstance(gate, Mapping):
        return "MISSING"
    return str(gate.get("status", "MISSING")).upper()


def _positive_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise CycleError(f"campaign authorization {field} must be a positive integer")
    return value


def validate_campaign_authorization(
    current_state: Mapping[str, Any],
    *,
    start_experiment_id: str,
    requested_iterations: int,
    requested_role_steps: int | None,
) -> CampaignAuthorization:
    """Validate an A-owned authorization without creating or widening it."""

    raw = current_state.get("bounded_campaign_authorization")
    if not isinstance(raw, Mapping):
        raise CycleError("missing A-recorded bounded_campaign_authorization")
    if str(raw.get("status", "")).upper() != "ALLOWED":
        raise CycleError("bounded campaign authorization is not ALLOWED")
    if raw.get("data_mode") != "train_valid_only":
        raise CycleError("bounded campaign must be train_valid_only")
    if raw.get("automatic_public_valid") is not True:
        raise CycleError("bounded campaign does not authorize automatic public validation")
    if raw.get("test_access") is not False:
        raise CycleError("bounded campaign must explicitly forbid test access")
    if raw.get("final_approval_allowed") is not False:
        raise CycleError("bounded campaign must explicitly forbid final approval")

    supplied_ids = raw.get("experiment_ids")
    if not isinstance(supplied_ids, list) or not supplied_ids:
        raise CycleError("campaign authorization experiment_ids must be a non-empty list")
    experiment_ids = tuple(str(item) for item in supplied_ids)
    if len(set(experiment_ids)) != len(experiment_ids):
        raise CycleError("campaign authorization experiment_ids contains duplicates")
    for index, experiment_id in enumerate(experiment_ids):
        if not EXPERIMENT_RE.fullmatch(experiment_id):
            raise CycleError(f"invalid campaign experiment identifier: {experiment_id}")
        if index and experiment_id != next_experiment_id(experiment_ids[index - 1]):
            raise CycleError("campaign authorization experiment_ids must be consecutive")

    maximum = _positive_int(
        raw.get("max_completed_experiments"), "max_completed_experiments"
    )
    max_role_steps = _positive_int(raw.get("max_role_steps"), "max_role_steps")
    if maximum > len(experiment_ids):
        raise CycleError("campaign maximum exceeds its explicit experiment_ids")
    if requested_iterations <= 0:
        raise CycleError("--max-iterations must be a positive integer")
    if requested_iterations > maximum:
        raise CycleError("requested iterations exceed A-recorded campaign maximum")
    if start_experiment_id not in experiment_ids:
        raise CycleError("requested start experiment is outside the A-recorded campaign")
    start_index = experiment_ids.index(start_experiment_id)
    if start_index + requested_iterations > len(experiment_ids):
        raise CycleError("requested iterations exceed the authorized experiment range")
    if requested_role_steps is not None:
        if requested_role_steps <= 0:
            raise CycleError("--max-role-steps must be a positive integer")
        if requested_role_steps > max_role_steps:
            raise CycleError("requested role steps exceed A-recorded campaign maximum")

    canonical = json.dumps(raw, sort_keys=True, separators=(",", ":"))
    return CampaignAuthorization(
        experiment_ids=experiment_ids,
        max_completed_experiments=maximum,
        max_role_steps=max_role_steps,
        automatic_public_valid=True,
        authorization_hash=hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
    )


def completed_experiment_ids(records: Sequence[Mapping[str, Any]]) -> set[str]:
    return {
        str(record["experiment_id"])
        for record in records
        if record.get("record_type") == "experiment_decision"
        and isinstance(record.get("experiment_id"), str)
        and EXPERIMENT_RE.fullmatch(str(record["experiment_id"]))
    }


def repository_progress_fingerprint(repo: Path) -> str:
    """Hash only A-owned routing/decision state used to authorize the next step."""

    digest = hashlib.sha256()
    for relative in (
        "coordination/current_experiment.json",
        "coordination/current_state.json",
        "coordination/experiment_history.jsonl",
    ):
        path = repo / relative
        if not path.is_file():
            raise CycleError(f"missing campaign progress file: {relative}")
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def consecutive_no_improve_limit(repo: Path) -> int:
    policy = load_json(repo / "governance" / "policy.json")
    return _positive_int(
        policy.get("consecutive_no_improve"), "policy consecutive_no_improve"
    )


def current_no_improve_count(current_state: Mapping[str, Any]) -> int:
    value = current_state.get("consecutive_no_improve", 0)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise CycleError("current consecutive_no_improve must be a non-negative integer")
    return value


def build_role_prompt(
    *,
    role: str,
    experiment_id: str,
    gate_status: str,
    allow_real_valid: bool,
    campaign_public_valid_authorized: bool = False,
) -> str:
    formal_run_allowed = (
        role == "B"
        and gate_status == "ALLOWED"
        and (allow_real_valid or campaign_public_valid_authorized)
    )
    formal_evaluation_allowed = (
        role == "E"
        and gate_status == "ALLOWED"
        and campaign_public_valid_authorized
    )
    if formal_run_allowed and campaign_public_valid_authorized:
        formal_instruction = (
            "A's recorded REAL_VALID gate is ALLOWED and the invocation is inside "
            "A's bounded train-valid-only campaign. Execute only the approved "
            "valid-only run; this does not authorize hidden-test or final-release work."
        )
    elif formal_run_allowed:
        formal_instruction = (
            "A's recorded REAL_VALID gate is ALLOWED and this invocation explicitly "
            "permits B to execute only the approved valid-only run."
        )
    elif formal_evaluation_allowed:
        formal_instruction = (
            "A's bounded train-valid-only campaign and REAL_VALID gate are ALLOWED. "
            "Do not train. Independently evaluate only B's immutable approved validation "
            "artifacts; hidden-test and final-release work remain forbidden."
        )
    else:
        formal_instruction = (
            "Do not run real data training or produce formal validation metrics."
        )
    return f"""You are Track 2 role {role} continuing {experiment_id} asynchronously.

Read AGENTS.md, .codex/agents/{role}.toml, coordination/current_state.json,
coordination/current_experiment.json, and the applicable experiment evidence.
Stay within role {role}'s write authority. Work on the already prepared role
branch, preserve user files, use a pull request, and never commit generated
data, predictions, checkpoints, credentials, or artifacts.

Safety constraints:
- Never access, compute, print, or report test labels or test metrics.
- Never use quarantined PR #25 evidence.
- Never create final approval.
- {formal_instruction}
- Small evidence may be committed through the PR. Large artifacts must remain
  local and be listed in large_artifact_paths for manual private transfer.
- If a prerequisite is absent, return BLOCKED instead of inventing evidence.

Complete only role {role}'s currently legal next step for {experiment_id}, run
the repository checks required by AGENTS.md, push the role branch, and create a
PR without merging it. Your final response must satisfy the supplied JSON
schema. Set test_access, pr_25_evidence_used, and final_approval_created false.
"""


def find_codex_executable() -> str:
    candidates = ["codex.cmd", "codex"] if os.name == "nt" else ["codex"]
    for candidate in candidates:
        found = shutil.which(candidate)
        if found:
            return found
    raise CycleError("Codex CLI was not found on PATH")


def build_codex_command(
    *,
    executable: str,
    worktree: Path,
    schema: Path,
    last_message: Path,
    session_id: str | None = None,
) -> list[str]:
    if session_id:
        return [
            executable,
            "exec",
            "resume",
            session_id,
            "--output-schema",
            str(schema),
            "--json",
            "-o",
            str(last_message),
            "-",
        ]
    return [
        executable,
        "exec",
        "-C",
        str(worktree),
        "-s",
        "workspace-write",
        "--output-schema",
        str(schema),
        "--json",
        "-o",
        str(last_message),
        "-",
    ]


def validate_agent_result(
    value: Mapping[str, Any], *, role: str, experiment_id: str
) -> None:
    required = {
        "status",
        "role",
        "phase",
        "experiment_id",
        "summary",
        "commit_sha",
        "pr_url",
        "small_evidence_paths",
        "large_artifact_paths",
        "next_receiver",
        "formal_metrics_produced",
        "pr_25_evidence_used",
        "final_approval_created",
        "test_access",
    }
    missing = sorted(required - set(value))
    if missing:
        raise CycleError(f"agent result is missing fields: {', '.join(missing)}")
    if value["role"] != role or value["experiment_id"] != experiment_id:
        raise CycleError("agent result role or experiment_id does not match dispatch")
    if value["status"] not in {"COMPLETED", "WAITING", "BLOCKED", "FAILED"}:
        raise CycleError(f"invalid agent status: {value['status']}")
    for field in ("test_access", "pr_25_evidence_used", "final_approval_created"):
        if value[field] is not False:
            raise CycleError(f"unsafe agent result: {field} must be false")
    if not isinstance(value["formal_metrics_produced"], bool):
        raise CycleError("agent result formal_metrics_produced must be boolean")
    if value["formal_metrics_produced"] and role != "E":
        raise CycleError("only independent evaluator E may report formal metrics")
    sha = value.get("commit_sha")
    if sha is not None and not SHA_RE.fullmatch(str(sha)):
        raise CycleError("agent result commit_sha must be a full lowercase SHA")
    for field in ("small_evidence_paths", "large_artifact_paths"):
        if not isinstance(value[field], list) or not all(
            isinstance(item, str) for item in value[field]
        ):
            raise CycleError(f"agent result {field} must be an array of paths")
        if len(value[field]) != len(set(value[field])):
            raise CycleError(f"agent result {field} must not contain duplicate paths")
    normalize_receivers(value.get("next_receiver"))


def safe_branch_name(role: str, experiment_id: str) -> str:
    return f"{role}/{experiment_id}-auto"


def fast_forward_to_origin_main(worktree: Path, *, label: str) -> str:
    """Refresh a clean checkout without rebasing, resetting, or rewriting history."""

    require_clean_worktree(worktree)
    head = require_success(
        run_command(("git", "rev-parse", "HEAD"), cwd=worktree), f"{label} HEAD"
    )
    origin_main = require_success(
        run_command(("git", "rev-parse", "origin/main"), cwd=worktree),
        f"{label} origin/main",
    )
    if head == origin_main:
        return head
    ancestor = run_command(
        ("git", "merge-base", "--is-ancestor", head, origin_main), cwd=worktree
    )
    if ancestor.returncode != 0:
        raise CycleError(
            f"{label} cannot fast-forward to origin/main; refusing rebase or reset"
        )
    require_success(
        run_command(("git", "merge", "--ff-only", "origin/main"), cwd=worktree),
        f"{label} fast-forward",
    )
    return require_clean_worktree(worktree)


def sync_main_checkout(repo: Path) -> str:
    branch = require_success(
        run_command(("git", "branch", "--show-current"), cwd=repo),
        "current branch lookup",
    )
    if branch != "main":
        raise CycleError("continuous run must be launched from the clean main checkout")
    require_success(run_command(("git", "fetch", "origin", "main"), cwd=repo), "git fetch")
    return fast_forward_to_origin_main(repo, label="main checkout")


def prepare_role_worktree(
    repo: Path, *, role: str, experiment_id: str, worktree_root: Path | None
) -> Path:
    require_success(run_command(("git", "fetch", "origin", "main"), cwd=repo), "git fetch")
    root = worktree_root or (
        Path(tempfile.gettempdir())
        / "bob-agent-cycle"
        / hashlib.sha256(str(repo).encode("utf-8")).hexdigest()[:12]
    )
    path = (root / experiment_id / role.lower()).resolve()
    branch = safe_branch_name(role, experiment_id)
    if path.exists():
        try:
            actual = repository_root(path)
        except CycleError as exc:
            raise CycleError(f"existing role worktree is invalid: {path}") from exc
        if actual != path:
            raise CycleError(f"existing role worktree resolves unexpectedly: {actual}")
        fast_forward_to_origin_main(path, label=f"existing {role} role worktree")
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    branch_exists = run_command(
        ("git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"), cwd=repo
    ).returncode == 0
    if branch_exists:
        raise CycleError(
            f"local branch {branch} exists without its recorded worktree; inspect manually"
        )
    require_success(
        run_command(
            ("git", "worktree", "add", "-b", branch, str(path), "origin/main"),
            cwd=repo,
        ),
        "role worktree creation",
    )
    return path


def extract_session_id(events_text: str) -> str | None:
    for line in events_text.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "thread.started":
            value = event.get("thread_id") or event.get("session_id")
            if isinstance(value, str) and value:
                return value
    return None


def dispatch_role(
    repo: Path,
    runtime: Path,
    *,
    role: str,
    experiment_id: str,
    gate_status: str,
    allow_real_valid: bool,
    worktree_root: Path | None,
    resume_session: str | None,
    campaign_public_valid_authorized: bool = False,
    execution_timeout_seconds: int | None = None,
) -> dict[str, Any]:
    worktree = prepare_role_worktree(
        repo, role=role, experiment_id=experiment_id, worktree_root=worktree_root
    )
    role_runtime = runtime / role.lower()
    role_runtime.mkdir(parents=True, exist_ok=True)
    schema = repo / "contracts" / "agent_cycle_result.schema.json"
    last_message = role_runtime / "last_message.json"
    events = role_runtime / "events.jsonl"
    command = build_codex_command(
        executable=find_codex_executable(),
        worktree=worktree,
        schema=schema,
        last_message=last_message,
        session_id=resume_session,
    )
    prompt = build_role_prompt(
        role=role,
        experiment_id=experiment_id,
        gate_status=gate_status,
        allow_real_valid=allow_real_valid,
        campaign_public_valid_authorized=campaign_public_valid_authorized,
    )
    result = run_command(
        command,
        cwd=worktree,
        input_text=prompt,
        timeout_seconds=execution_timeout_seconds,
    )
    events.write_text(result.stdout, encoding="utf-8")
    session_id = extract_session_id(result.stdout)
    if result.returncode != 0:
        write_json(
            role_runtime / "stopped_manifest.json",
            {
                "status": "STOPPED",
                "role": role,
                "experiment_id": experiment_id,
                "exit_code": result.returncode,
                "session_id": session_id,
                "recorded_at_utc": utc_now(),
                "test_access": False,
            },
        )
        detail = result.stderr.strip() or "see events.jsonl"
        raise CycleError(f"Codex role execution stopped: {detail}")
    value = load_json(last_message)
    validate_agent_result(value, role=role, experiment_id=experiment_id)
    value = dict(value)
    value["session_id"] = session_id
    value["role_worktree"] = str(worktree)
    write_json(role_runtime / "result.json", value)
    return value


def artifact_inventory(paths: Iterable[Path]) -> list[dict[str, Any]]:
    inventory: list[dict[str, Any]] = []
    for supplied in paths:
        path = supplied.resolve()
        if not path.exists():
            raise CycleError(f"artifact path does not exist: {path}")
        files = [path] if path.is_file() else sorted(item for item in path.rglob("*") if item.is_file())
        base = path.parent if path.is_file() else path
        for file_path in files:
            if file_path.is_symlink():
                raise CycleError(f"symlink artifacts are not accepted: {file_path}")
            inventory.append(
                {
                    "source_root": str(path),
                    "relative_path": file_path.relative_to(base).as_posix(),
                    "size_bytes": file_path.stat().st_size,
                    "sha256": sha256_file(file_path),
                }
            )
    return inventory


def create_handoff_manifest(
    runtime: Path,
    *,
    experiment_id: str,
    recipient: str,
    artifact_paths: Sequence[Path],
) -> Path:
    if recipient not in ROLES:
        raise CycleError(f"invalid recipient role: {recipient}")
    manifest_path = runtime / "handoff" / f"to_{recipient.lower()}.json"
    write_json(
        manifest_path,
        {
            "schema_version": 1,
            "experiment_id": experiment_id,
            "recipient": recipient,
            "manual_private_transfer_required": True,
            "git_upload_allowed": False,
            "created_at_utc": utc_now(),
            "files": artifact_inventory(artifact_paths),
            "test_access": False,
        },
    )
    return manifest_path


def parse_history(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise CycleError(f"invalid history JSONL line {number}: {exc}") from exc
        if isinstance(value, dict):
            records.append(value)
    return records


def experiment_comparison(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    comparison: list[dict[str, Any]] = []
    for record in records:
        if record.get("record_type") != "experiment_decision":
            continue
        comparison.append(
            {
                "experiment_id": record.get("experiment_id"),
                "decision": record.get("decision"),
                "baseline_primary": record.get("baseline_primary"),
                "candidate_primary": record.get("candidate_primary"),
                "primary_delta": record.get("primary_delta"),
                "test_access": record.get("test_access"),
            }
        )
    return comparison


def render_status_markdown(report: Mapping[str, Any]) -> str:
    lines = [
        f"# Agent cycle status: {report['target_experiment_id']}",
        "",
        f"- Generated: `{report['generated_at_utc']}`",
        f"- Current repository experiment: `{report['repository_experiment_id']}`",
        f"- Current champion: `{report['champion_experiment_id']}`",
        f"- Next receiver(s): `{', '.join(report['next_receivers']) or 'none'}`",
        f"- REAL_VALID gate: `{report['real_valid_gate_status']}`",
        f"- Test access: `{str(report['test_access']).lower()}`",
        "",
        "## Experiment comparison",
        "",
        "| Experiment | Decision | Baseline primary | Candidate primary | Delta |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in report["experiment_comparison"]:
        lines.append(
            "| {experiment_id} | {decision} | {baseline_primary} | "
            "{candidate_primary} | {primary_delta} |".format(**row)
        )
    lines.extend(
        [
            "",
            "## Demo summary",
            "",
            "The coordinator reads governance state, dispatches only the legal next role, "
            "waits for reviewable PR evidence, and keeps large artifacts outside Git.",
            f"The verified champion is {report['champion_experiment_id']}; "
            "the next experiment remains uncreated until A proposes it.",
            "Hidden test was never accessed by this report or the recorded ordinary cycle.",
            "",
        ]
    )
    return "\n".join(lines)


def generate_reports(
    repo: Path,
    runtime: Path,
    *,
    target: str,
    current_experiment: Mapping[str, Any],
    current_state: Mapping[str, Any],
) -> dict[str, Any]:
    receivers = determine_receivers(target, current_experiment, current_state)
    comparison = experiment_comparison(
        parse_history(repo / "coordination" / "experiment_history.jsonl")
    )
    report = {
        "schema_version": 1,
        "generated_at_utc": utc_now(),
        "target_experiment_id": target,
        "repository_experiment_id": current_experiment.get("experiment_id"),
        "repository_status": current_experiment.get("status"),
        "champion_experiment_id": current_experiment.get(
            "retained_champion_experiment_id",
            current_experiment.get("experiment_id"),
        ),
        "next_receivers": receivers,
        "real_valid_gate_status": real_valid_gate_status(current_state),
        "experiment_comparison": comparison,
        "manual_large_artifact_transfer": True,
        "test_access": False,
    }
    write_json(runtime / "cycle_state.json", report)
    (runtime / "status.md").write_text(
        render_status_markdown(report), encoding="utf-8"
    )
    write_json(
        runtime / "demo_summary.json",
        {
            "experiment_id": target,
            "current_status": current_experiment.get("status"),
            "champion_experiment_id": report["champion_experiment_id"],
            "next_receivers": receivers,
            "completed_experiments": len(comparison),
            "capabilities": [
                "state_driven_role_dispatch",
                "Codex_session_resume",
                "PR_and_CI_gate_monitoring",
                "hashed_manual_artifact_handoff",
                "cycle_status_and_experiment_comparison",
            ],
            "test_access": False,
        },
    )
    return report


def role_owns_path(role: str, path: str) -> bool:
    """Conservative auto-merge allowlist derived from AGENTS.md ownership."""

    if path.startswith(f"coordination/inbox/{role}/"):
        return True
    if role == "A":
        return (
            path == "AGENTS.md"
            or path == "README.md"
            or path.startswith("governance/")
            or path.startswith(".github/")
            or path.startswith(".codex/")
            or path.startswith("experiments/")
            or path.startswith("configs/approved/")
            or path.startswith("coordination/iterations/")
            or path.startswith("reports/decisions/")
            or path.startswith("docs/")
            or path
            in {
                "coordination/current_state.json",
                "coordination/current_experiment.json",
                "coordination/experiment_history.jsonl",
            }
        )
    if role == "B":
        return (
            path.startswith("tests/")
            or path.startswith("contracts/")
            or path.startswith("scripts/")
            or (path.startswith("tools/") and path not in E_OWNED_TOOL_PATHS)
            or path.startswith("reports/bootstrap/")
        )
    if role == "C":
        return path.startswith("src/data/")
    if role == "D":
        return (
            path.startswith("src/models/")
            or path.startswith("src/training/")
            or path.startswith("configs/candidates/")
        )
    if role == "E":
        return (
            path.startswith("evaluation/")
            or path in E_OWNED_TOOL_PATHS
            or path.startswith("reports/evaluation/")
            or path.startswith("coordination/results/")
        )
    return False


def assess_pr(
    pr: Mapping[str, Any],
    *,
    expected_head_sha: str | None = None,
    expected_role: str | None = None,
) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if pr.get("state") != "OPEN":
        reasons.append(f"PR state is {pr.get('state')}, not OPEN")
    if pr.get("mergeable") != "MERGEABLE":
        reasons.append(f"PR mergeable is {pr.get('mergeable')}")
    files = {
        str(item.get("path", ""))
        for item in pr.get("files", [])
        if isinstance(item, Mapping)
    }
    unsafe = sorted(
        path
        for path in files
        if path.startswith("starter/")
        or path in PROTECTED_AUTOMERGE_PATHS
        or path in RELEASE_ONLY_AUTOMERGE_PATHS
        or "/final_approval" in path
    )
    if unsafe:
        reasons.append("protected paths require human review: " + ", ".join(unsafe))
    if expected_role is not None:
        ownership_conflicts = sorted(
            path for path in files if not role_owns_path(expected_role, path)
        )
        if ownership_conflicts:
            reasons.append(
                f"role {expected_role} does not own changed paths: "
                + ", ".join(ownership_conflicts)
            )
    if expected_head_sha is not None and pr.get("headRefOid") != expected_head_sha:
        reasons.append(
            "PR head does not match dispatched role commit: "
            f"expected {expected_head_sha}, observed {pr.get('headRefOid', 'MISSING')}"
        )
    checks = pr.get("statusCheckRollup", [])
    observed: dict[str, str] = {}
    for check in checks if isinstance(checks, list) else []:
        if not isinstance(check, Mapping):
            continue
        workflow = check.get("workflowName")
        name = check.get("name") or check.get("context")
        full = f"{workflow} / {name}" if workflow and name else str(name or workflow or "")
        observed[full] = str(check.get("conclusion") or check.get("state") or "")
    for required in sorted(REQUIRED_CHECKS):
        if observed.get(required) not in {"SUCCESS", "NEUTRAL", "SKIPPED"}:
            reasons.append(
                f"required check not successful: {required}={observed.get(required, 'MISSING')}"
            )
    return not reasons, reasons


def load_pr(repo: Path, pr_number: int) -> dict[str, Any]:
    fields = "number,url,state,mergeable,mergeStateStatus,headRefOid,files,statusCheckRollup"
    stdout = require_success(
        run_command(
            ("gh", "pr", "view", str(pr_number), "--json", fields), cwd=repo
        ),
        "GitHub PR lookup",
    )
    value = json.loads(stdout)
    if not isinstance(value, dict):
        raise CycleError("GitHub PR response was not an object")
    return value


def watch_pr(
    repo: Path,
    *,
    pr_number: int,
    timeout_seconds: int,
    poll_seconds: int,
    auto_merge: bool,
    expected_head_sha: str | None = None,
    expected_role: str | None = None,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    while True:
        pr = load_pr(repo, pr_number)
        ready, reasons = assess_pr(
            pr,
            expected_head_sha=expected_head_sha,
            expected_role=expected_role,
        )
        if ready:
            if auto_merge:
                require_success(
                    run_command(
                        ("gh", "pr", "merge", str(pr_number), "--merge"),
                        cwd=repo,
                    ),
                    "GitHub PR merge",
                )
                pr = load_pr(repo, pr_number)
                if pr.get("state") != "MERGED":
                    return {
                        "ready": False,
                        "reasons": ["PR merge command completed but state is not MERGED"],
                        "pr": pr,
                    }
            return {"ready": True, "reasons": [], "pr": pr}
        pending_only = reasons and all(
            reason.startswith("required check not successful") for reason in reasons
        )
        if not pending_only or time.monotonic() >= deadline:
            return {"ready": False, "reasons": reasons, "pr": pr}
        time.sleep(poll_seconds)


def parse_pr_number(pr_url: Any) -> int | None:
    if not isinstance(pr_url, str):
        return None
    match = re.search(r"/pull/(\d+)(?:$|[/?#])", pr_url)
    return int(match.group(1)) if match else None


def _campaign_state_path(runtime: Path) -> Path:
    return runtime / "campaign_state.json"


def _record_campaign_stop(
    runtime: Path,
    campaign_state: dict[str, Any],
    *,
    reason: str,
    detail: str,
) -> None:
    campaign_state.update(
        {
            "status": "STOPPED",
            "stop_reason": reason,
            "stop_detail": detail,
            "updated_at_utc": utc_now(),
            "test_access": False,
            "final_approval_created": False,
        }
    )
    write_json(_campaign_state_path(runtime), campaign_state)


def _load_or_initialize_campaign_state(
    runtime: Path,
    *,
    start_experiment_id: str,
    authorized_experiment_ids: Sequence[str],
    max_iterations: int,
    max_role_steps: int,
    authorization_hash: str,
    existing_decisions: set[str],
) -> dict[str, Any]:
    path = _campaign_state_path(runtime)
    expected_ids = list(authorized_experiment_ids)
    if path.exists():
        value = load_json(path)
        expected = {
            "start_experiment_id": start_experiment_id,
            "authorized_experiment_ids": expected_ids,
            "max_iterations": max_iterations,
            "max_role_steps": max_role_steps,
            "authorization_hash": authorization_hash,
        }
        mismatched = [key for key, item in expected.items() if value.get(key) != item]
        if mismatched:
            raise CycleError(
                "existing campaign state does not match this invocation: "
                + ", ".join(mismatched)
            )
        if value.get("test_access") is not False:
            raise CycleError("existing campaign state does not preserve test isolation")
        return value

    if start_experiment_id in existing_decisions:
        raise CycleError(
            "start experiment was already completed; choose the next experiment or resume its existing campaign state"
        )
    value = {
        "schema_version": 1,
        "status": "RUNNING",
        "start_experiment_id": start_experiment_id,
        "authorized_experiment_ids": expected_ids,
        "max_iterations": max_iterations,
        "max_role_steps": max_role_steps,
        "role_steps_completed": 0,
        "completed_experiment_ids": [],
        "decisions_present_at_start": sorted(existing_decisions),
        "authorization_hash": authorization_hash,
        "created_at_utc": utc_now(),
        "updated_at_utc": utc_now(),
        "test_access": False,
        "final_approval_created": False,
    }
    write_json(path, value)
    return value


def _refresh_campaign_completion(
    campaign_state: dict[str, Any], records: Sequence[Mapping[str, Any]]
) -> list[str]:
    decided = completed_experiment_ids(records)
    initial = set(campaign_state["decisions_present_at_start"])
    completed = [
        experiment_id
        for experiment_id in campaign_state["authorized_experiment_ids"]
        if experiment_id in decided and experiment_id not in initial
    ]
    campaign_state["completed_experiment_ids"] = completed
    campaign_state["updated_at_utc"] = utc_now()
    return completed


def run_campaign(repo: Path, args: argparse.Namespace) -> int:
    """Run reviewed role PRs until the bounded goal or a truthful stop point."""

    sync_main_checkout(repo)
    verify_protected(repo)
    current_experiment = load_json(repo / "coordination" / "current_experiment.json")
    current_state = load_json(repo / "coordination" / "current_state.json")
    start_target = select_target_experiment(
        args.experiment, current_experiment, current_state
    )
    authorization = validate_campaign_authorization(
        current_state,
        start_experiment_id=start_target,
        requested_iterations=args.max_iterations,
        requested_role_steps=args.max_role_steps,
    )
    start_index = authorization.experiment_ids.index(start_target)
    authorized_ids = authorization.experiment_ids[
        start_index : start_index + args.max_iterations
    ]
    effective_role_steps = args.max_role_steps or authorization.max_role_steps
    runtime = (
        args.runtime_root.resolve()
        if args.runtime_root
        else repo / "artifacts" / "agent_cycle" / f"campaign_{start_target}"
    )
    history_path = repo / "coordination" / "experiment_history.jsonl"
    initial_records = parse_history(history_path)
    campaign_state = _load_or_initialize_campaign_state(
        runtime,
        start_experiment_id=start_target,
        authorized_experiment_ids=authorized_ids,
        max_iterations=args.max_iterations,
        max_role_steps=effective_role_steps,
        authorization_hash=authorization.authorization_hash,
        existing_decisions=completed_experiment_ids(initial_records),
    )
    policy = load_json(repo / "governance" / "policy.json")
    execution_timeout = _positive_int(
        policy.get("max_single_round_seconds"), "policy max_single_round_seconds"
    )
    no_improve_limit = consecutive_no_improve_limit(repo)

    while True:
        current_experiment = load_json(
            repo / "coordination" / "current_experiment.json"
        )
        current_state = load_json(repo / "coordination" / "current_state.json")
        refreshed_authorization = validate_campaign_authorization(
            current_state,
            start_experiment_id=start_target,
            requested_iterations=args.max_iterations,
            requested_role_steps=effective_role_steps,
        )
        if refreshed_authorization.authorization_hash != authorization.authorization_hash:
            _record_campaign_stop(
                runtime,
                campaign_state,
                reason="AUTHORIZATION_CHANGED",
                detail="A-recorded campaign authorization changed during execution",
            )
            raise CycleError("campaign authorization changed during execution")

        history_records = parse_history(history_path)
        all_decisions = completed_experiment_ids(history_records)
        active_id = str(current_experiment.get("experiment_id", ""))
        if (
            active_id in authorized_ids
            and is_terminal_state(current_experiment)
            and active_id not in all_decisions
        ):
            _record_campaign_stop(
                runtime,
                campaign_state,
                reason="TERMINAL_DECISION_MISSING_FROM_HISTORY",
                detail=f"terminal {active_id} has no experiment_decision history record",
            )
            raise CycleError("terminal experiment is missing canonical decision history")
        completed = _refresh_campaign_completion(campaign_state, history_records)
        if len(completed) >= args.max_iterations:
            campaign_state.update(
                {
                    "status": "COMPLETED",
                    "stop_reason": "MAX_ITERATIONS_COMPLETED",
                    "updated_at_utc": utc_now(),
                    "test_access": False,
                    "final_approval_created": False,
                }
            )
            write_json(_campaign_state_path(runtime), campaign_state)
            print(json.dumps(campaign_state, indent=2, ensure_ascii=False))
            return 0
        if current_no_improve_count(current_state) >= no_improve_limit:
            _record_campaign_stop(
                runtime,
                campaign_state,
                reason="NO_IMPROVEMENT_STOP_RULE",
                detail="policy consecutive-no-improvement limit reached",
            )
            raise CycleError("campaign reached the consecutive no-improvement stop rule")
        if campaign_state["role_steps_completed"] >= effective_role_steps:
            _record_campaign_stop(
                runtime,
                campaign_state,
                reason="MAX_ROLE_STEPS",
                detail="A-recorded role-step bound reached",
            )
            raise CycleError("campaign reached its maximum role-step bound")

        remaining = [item for item in authorized_ids if item not in completed]
        target = remaining[0]
        select_target_experiment(target, current_experiment, current_state)
        target_runtime = runtime / "experiments" / target
        report = generate_reports(
            repo,
            target_runtime,
            target=target,
            current_experiment=current_experiment,
            current_state=current_state,
        )
        receivers = report["next_receivers"]
        if not receivers:
            _record_campaign_stop(
                runtime,
                campaign_state,
                reason="NO_LEGAL_RECEIVER",
                detail=f"repository has no legal receiver for {target}",
            )
            raise CycleError("repository state has no legal next receiver")
        role = receivers[0]
        gate_status = report["real_valid_gate_status"]
        campaign_public_valid = gate_status == "ALLOWED"
        progress_before = repository_progress_fingerprint(repo)
        result = dispatch_role(
            repo,
            target_runtime,
            role=role,
            experiment_id=target,
            gate_status=gate_status,
            allow_real_valid=False,
            worktree_root=args.worktree_root,
            resume_session=None,
            campaign_public_valid_authorized=campaign_public_valid,
            execution_timeout_seconds=execution_timeout,
        )
        role_worktree = Path(result["role_worktree"])
        produced_head = require_clean_worktree(role_worktree)
        if produced_head != result.get("commit_sha"):
            _record_campaign_stop(
                runtime,
                campaign_state,
                reason="ROLE_COMMIT_MISMATCH",
                detail=(
                    f"role result declared {result.get('commit_sha')} but clean worktree "
                    f"HEAD is {produced_head}"
                ),
            )
            raise CycleError("role result commit does not match its clean worktree HEAD")
        campaign_state["role_steps_completed"] += 1
        campaign_state["last_role"] = role
        campaign_state["last_experiment_id"] = target
        campaign_state["updated_at_utc"] = utc_now()
        write_json(_campaign_state_path(runtime), campaign_state)

        if result["status"] != "COMPLETED":
            _record_campaign_stop(
                runtime,
                campaign_state,
                reason=f"ROLE_{result['status']}",
                detail=str(result.get("summary", "role did not complete")),
            )
            raise CycleError(f"role {role} returned {result['status']}")
        pr_number = parse_pr_number(result.get("pr_url"))
        if pr_number is None:
            _record_campaign_stop(
                runtime,
                campaign_state,
                reason="MISSING_PR",
                detail=f"completed role {role} did not return a reviewable PR",
            )
            raise CycleError("completed campaign role did not return a PR URL")
        pr_result = watch_pr(
            repo,
            pr_number=pr_number,
            timeout_seconds=max(0, args.timeout_seconds),
            poll_seconds=max(5, min(60, args.poll_seconds)),
            auto_merge=True,
            expected_head_sha=str(result["commit_sha"]),
            expected_role=role,
        )
        if not pr_result["ready"]:
            detail = "; ".join(pr_result["reasons"])
            _record_campaign_stop(
                runtime,
                campaign_state,
                reason="PR_GATE_BLOCKED",
                detail=detail,
            )
            raise CycleError(f"PR gate blocked continuous campaign: {detail}")

        sync_main_checkout(repo)
        verify_protected(repo)
        progress_after = repository_progress_fingerprint(repo)
        large_paths = [
            supplied if supplied.is_absolute() else role_worktree / supplied
            for supplied in (
                Path(path) for path in result.get("large_artifact_paths", [])
            )
        ]
        if large_paths:
            next_receivers = normalize_receivers(result.get("next_receiver"))
            if not next_receivers:
                _record_campaign_stop(
                    runtime,
                    campaign_state,
                    reason="ARTIFACT_RECIPIENT_MISSING",
                    detail="large artifacts have no declared recipient",
                )
                raise CycleError("large artifacts have no declared recipient")
            manifest = create_handoff_manifest(
                target_runtime,
                experiment_id=target,
                recipient=next_receivers[0],
                artifact_paths=large_paths,
            )
            _record_campaign_stop(
                runtime,
                campaign_state,
                reason="MANUAL_ARTIFACT_TRANSFER_REQUIRED",
                detail=str(manifest),
            )
            raise CycleError("manual private artifact transfer is required")
        if progress_after == progress_before:
            _record_campaign_stop(
                runtime,
                campaign_state,
                reason="NO_STATE_PROGRESS",
                detail=(
                    f"role {role} PR merged, but A-owned routing/decision state did not change; "
                    "A must integrate or advance state before resume"
                ),
            )
            raise CycleError("merged role PR did not advance canonical campaign state")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Safely coordinate asynchronous Track 2 A-E experiment cycles."
    )
    parser.add_argument("--experiment", help="target experiment, for example exp_003")
    parser.add_argument(
        "--action",
        choices=("status", "step", "run", "watch-pr", "handoff", "report"),
        default="status",
    )
    parser.add_argument("--execute", action="store_true", help="actually invoke Codex")
    parser.add_argument("--worker-role", choices=ROLES)
    parser.add_argument("--allow-real-valid", action="store_true")
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=1,
        help="maximum newly completed experiments for --action run",
    )
    parser.add_argument(
        "--max-role-steps",
        type=int,
        help="optional tighter role-dispatch bound for --action run",
    )
    parser.add_argument("--auto-merge", action="store_true")
    parser.add_argument("--wait-pr", action="store_true")
    parser.add_argument("--pr", type=int, help="PR number for watch-pr")
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    parser.add_argument("--poll-seconds", type=int, default=20)
    parser.add_argument("--recipient", choices=ROLES)
    parser.add_argument("--artifact-path", action="append", default=[])
    parser.add_argument("--resume-session")
    parser.add_argument("--worktree-root", type=Path)
    parser.add_argument("--runtime-root", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        repo = repository_root()
        if args.action == "run":
            incompatible = []
            for active, flag in (
                (args.execute, "--execute"),
                (args.worker_role is not None, "--worker-role"),
                (args.allow_real_valid, "--allow-real-valid"),
                (args.auto_merge, "--auto-merge"),
                (args.wait_pr, "--wait-pr"),
                (args.pr is not None, "--pr"),
                (args.recipient is not None, "--recipient"),
                (bool(args.artifact_path), "--artifact-path"),
                (args.resume_session is not None, "--resume-session"),
            ):
                if active:
                    incompatible.append(flag)
            if incompatible:
                raise CycleError(
                    "--action run manages execution, PR merge, and resume state itself; "
                    "remove " + ", ".join(incompatible)
                )
            return run_campaign(repo, args)

        current_experiment = load_json(repo / "coordination" / "current_experiment.json")
        current_state = load_json(repo / "coordination" / "current_state.json")
        target = select_target_experiment(args.experiment, current_experiment, current_state)
        runtime = (
            args.runtime_root.resolve()
            if args.runtime_root
            else repo / "artifacts" / "agent_cycle" / target
        )
        report = generate_reports(
            repo,
            runtime,
            target=target,
            current_experiment=current_experiment,
            current_state=current_state,
        )

        if args.action in {"status", "report"}:
            print(render_status_markdown(report))
            print(f"STATUS_PATH={runtime / 'status.md'}")
            return 0

        if args.action == "handoff":
            if not args.recipient or not args.artifact_path:
                raise CycleError("handoff requires --recipient and --artifact-path")
            manifest = create_handoff_manifest(
                runtime,
                experiment_id=target,
                recipient=args.recipient,
                artifact_paths=[Path(path) for path in args.artifact_path],
            )
            print(f"STATUS=MANUAL_TRANSFER_REQUIRED\nHANDOFF_MANIFEST={manifest}")
            return 0

        if args.action == "watch-pr":
            if not args.pr:
                raise CycleError("watch-pr requires --pr")
            result = watch_pr(
                repo,
                pr_number=args.pr,
                timeout_seconds=max(0, args.timeout_seconds),
                poll_seconds=max(5, min(60, args.poll_seconds)),
                auto_merge=args.auto_merge,
            )
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0 if result["ready"] else 2

        if not args.execute:
            raise CycleError("step is dry-run by default; add --execute to invoke Codex")
        require_clean_worktree(repo)
        verify_protected(repo)
        receivers = report["next_receivers"]
        if not receivers:
            raise CycleError("repository state has no legal next receiver")
        if args.worker_role:
            if args.worker_role not in receivers:
                print(
                    f"STATUS=WAITING_FOR_ROLE\nWORKER_ROLE={args.worker_role}\n"
                    f"NEXT_RECEIVERS={','.join(receivers)}"
                )
                return 0
            role = args.worker_role
        else:
            role = receivers[0]
        gate_status = report["real_valid_gate_status"]
        if args.allow_real_valid and not (role == "B" and gate_status == "ALLOWED"):
            raise CycleError(
                "--allow-real-valid is valid only for B with recorded gate status ALLOWED"
            )
        result = dispatch_role(
            repo,
            runtime,
            role=role,
            experiment_id=target,
            gate_status=gate_status,
            allow_real_valid=args.allow_real_valid,
            worktree_root=args.worktree_root,
            resume_session=args.resume_session,
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))
        role_worktree = Path(result["role_worktree"])
        large_paths = [
            supplied if supplied.is_absolute() else role_worktree / supplied
            for supplied in (Path(path) for path in result["large_artifact_paths"])
        ]
        if large_paths and result.get("next_receiver"):
            manifest = create_handoff_manifest(
                runtime,
                experiment_id=target,
                recipient=normalize_receivers(result["next_receiver"])[0],
                artifact_paths=large_paths,
            )
            print(f"MANUAL_TRANSFER_MANIFEST={manifest}")
        pr_number = parse_pr_number(result.get("pr_url"))
        if args.wait_pr and pr_number:
            pr_result = watch_pr(
                repo,
                pr_number=pr_number,
                timeout_seconds=max(0, args.timeout_seconds),
                poll_seconds=max(5, min(60, args.poll_seconds)),
                auto_merge=args.auto_merge,
                expected_head_sha=str(result["commit_sha"]),
                expected_role=role,
            )
            print(json.dumps(pr_result, indent=2, ensure_ascii=False))
            return 0 if pr_result["ready"] else 2
        return 0
    except (CycleError, OSError, json.JSONDecodeError) as exc:
        print(f"STATUS=BLOCKED\nERROR={exc}\ntest_access=false", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
